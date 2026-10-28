"""Turn embedded post records and media metadata into JSON-native values."""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import math
import re
import xml.etree.ElementTree as ET

from PIL import ExifTags
from PIL.TiffImagePlugin import IFDRational


GBRD = "urn:gelbooru-random-downloader:metadata:1"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
DC = "http://purl.org/dc/elements/1.1/"
PREFIXES = {GBRD: "gbrd", RDF: "rdf", DC: "dc",
            "http://ns.adobe.com/exif/1.0/": "exif",
            "http://ns.adobe.com/tiff/1.0/": "tiff",
            "http://ns.adobe.com/xap/1.0/": "xmp",
            "http://ns.adobe.com/photoshop/1.0/": "photoshop"}
FIELDS = (
    "schema_version", "site", "post_id", "post_url", "tags", "rating", "title", "source_url",
    "uploader_name", "uploader_id", "score", "width", "height", "original_width", "original_height",
    "source_md5", "resized", "maximum_megapixels", "uploaded_at", "uploaded_at_raw",
)
XMP_FIELDS = {"".join(part.capitalize() for part in field.split("_")): field for field in FIELDS}
INTEGER_FIELDS = {"schema_version", "post_id", "uploader_id", "score", "width", "height",
                  "original_width", "original_height"}
MAX_PACKET_BYTES = 8 * 1024 * 1024


def upload_time(value):
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    # ExifTool-style dates are also used by some XMP producers.
    if re.match(r"^\d{4}:\d{2}:\d{2} ", value):
        value = value[:10].replace(":", "-") + value[10:]
    try:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is not None and parsed.utcoffset() is not None:
            return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except (ValueError, TypeError, OverflowError):
        pass
    return None


def json_value(value):
    """Summarize binary data, keeping text and numeric-looking strings intact."""
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"byte_length": len(value)}
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key in ("prompt", "workflow") and isinstance(item, str):
                try:
                    parsed = json.loads(item)
                    if isinstance(parsed, (dict, list)):
                        item = parsed
                except (ValueError, RecursionError):
                    pass
            result[str(key)] = json_value(item)
        return result
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if isinstance(value, IFDRational):
        return float(value) if value.denominator else str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, str):
        return value
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)


def _name(tag):
    if tag.startswith("{"):
        namespace, local = tag[1:].split("}", 1)
        if namespace in PREFIXES:
            return PREFIXES[namespace] + ":" + local
    return tag


def _xml_value(element):
    children = list(element)
    if not children:
        return element.get(f"{{{RDF}}}resource", element.text or "")
    if len(children) == 1 and children[0].tag in (f"{{{RDF}}}Bag", f"{{{RDF}}}Seq"):
        return [_xml_value(item) for item in children[0]]
    if len(children) == 1 and children[0].tag == f"{{{RDF}}}Alt":
        return {item.get("{http://www.w3.org/XML/1998/namespace}lang", "x-default"): _xml_value(item)
                for item in children[0]}
    return {_name(item.tag): _xml_value(item) for item in children}


def _record(value, warnings):
    try:
        record = json.loads(value) if isinstance(value, str) else value
        if not isinstance(record, dict) or type(record.get("schema_version")) is not int:
            raise ValueError("not a versioned object")
        if record["schema_version"] not in (1, 2):
            raise ValueError("unsupported schema version")
        return record
    except (ValueError, TypeError, RecursionError):
        warnings.append("Could not read the embedded Gelbooru JSON record; using remaining metadata.")
        return None


def parse_xmp(packets, warnings):
    records, individual, remaining = [], {}, {}
    seen = set()
    for packet in packets:
        if not isinstance(packet, (str, bytes)):
            continue
        try:
            if len(packet) > MAX_PACKET_BYTES:
                raise ValueError("packet too large")
            text = packet.decode("utf-8-sig") if isinstance(packet, bytes) else packet.lstrip("\ufeff")
            text = text.strip()
            if text in seen:
                continue
            seen.add(text)
            if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
                raise ValueError("XML declarations are not supported")
            root = ET.fromstring(text)
            descriptions = [description for rdf in root.iter(f"{{{RDF}}}RDF")
                            for description in rdf if description.tag == f"{{{RDF}}}Description"]
            for description in descriptions:
                properties = [(key, value) for key, value in description.attrib.items()
                              if key != f"{{{RDF}}}about"]
                properties.extend((element.tag, _xml_value(element)) for element in description)
                for tag, value in properties:
                    if tag == f"{{{GBRD}}}Record":
                        record = _record(value, warnings)
                        if record is not None:
                            records.append(record)
                    elif tag.startswith(f"{{{GBRD}}}") and tag.split("}", 1)[1] in XMP_FIELDS:
                        individual.setdefault(XMP_FIELDS[tag.split("}", 1)[1]], value)
                    else:
                        remaining.setdefault(_name(tag), value)
        except (ET.ParseError, ValueError, UnicodeError, RecursionError):
            warnings.append("Could not parse an embedded XMP packet; using remaining metadata.")
    return records, individual, remaining


def _coerce(field, value):
    if field in INTEGER_FIELDS:
        if isinstance(value, str) and re.fullmatch(r"[+-]?\d+", value.strip()):
            try:
                value = int(value)
            except ValueError:
                return None
        if type(value) is int and (field == "score" or value > 0):
            return value
    elif field == "resized":
        if type(value) is bool:
            return value
        if isinstance(value, str) and value.lower() in ("true", "false"):
            return value.lower() == "true"
    elif field == "maximum_megapixels":
        if isinstance(value, (str, float, int)) and not isinstance(value, bool):
            try:
                value = float(value)
                if math.isfinite(value) and value > 0:
                    return value
            except (ValueError, OverflowError):
                pass
    elif field == "tags":
        if isinstance(value, list) and all(isinstance(tag, str) for tag in value):
            return sorted(set(value))
    elif field == "uploaded_at":
        return upload_time(value)
    elif isinstance(value, str) and value.strip():
        return value
    return None


def _flat_record(record):
    value = dict(record)
    for group, prefix in (("saved_dimensions", ""), ("original_dimensions", "original_")):
        if isinstance(value.get(group), dict):
            for side in ("width", "height"):
                value.setdefault(prefix + side, value[group].get(side))
    if "uploaded_at" in value:
        value.setdefault("uploaded_at_raw", value["uploaded_at"])
    return value


def _standard_text(value):
    if isinstance(value, dict):
        return value.get("x-default") or next(iter(value.values()), None)
    return value


def _standard_fields(xmp, native):
    tags = xmp.get("dc:subject")
    if tags is None:
        tags = native.get("keywords", native.get("com.apple.quicktime.keywords"))
        if isinstance(tags, str):
            tags = [tag for tag in re.split(r"[;,]\s*", tags) if tag]
    return {"tags": tags, "title": _standard_text(xmp.get("dc:title", native.get("title"))),
            "description": _standard_text(xmp.get("dc:description", native.get("description", native.get("comment"))))}


def normalized_metadata(records, individual, xmp, native, dimensions, metadata, warnings):
    result = {}
    for source in [*(_flat_record(record) for record in records), _flat_record(individual)]:
        for field in FIELDS:
            value = _coerce(field, source.get(field))
            if value is not None:
                result.setdefault(field, value)
    if records or individual:
        version = records[0]["schema_version"] if records else result.get("schema_version")
        if version is not None:
            metadata["gelbooru_schema_version"] = version
        result["schema_version"] = 2
    for field, value in _standard_fields(xmp, native).items():
        value = _coerce(field, value)
        if value is not None:
            result.setdefault(field, value)
    if dimensions:
        for field, value in zip(("width", "height"), dimensions):
            value = _coerce(field, value)
            if value is not None:
                result[field] = value
    if warnings:
        metadata["warnings"] = list(dict.fromkeys(warnings))
    result["metadata"] = json_value(metadata)
    return result


def image_metadata(image):
    warnings = []
    exif_values = {}
    packets = []
    try:
        exif = image.getexif()
        for key, value in exif.items():
            if key == 700:  # XMP is parsed separately, never dumped as XML here.
                packets.append(value)
                continue
            if key in (34665, 34853):
                names = ExifTags.GPSTAGS if key == 34853 else ExifTags.TAGS
                value = {names.get(tag, str(tag)): item for tag, item in exif.get_ifd(key).items()}
            exif_values[ExifTags.TAGS.get(key, str(key))] = value
    except Exception:
        warnings.append("Could not decode embedded EXIF metadata.")
    info = dict(image.info or {})
    for field in ("comment", "description"):
        if isinstance(info.get(field), bytes):
            try:
                info[field] = info[field].decode("utf-8")
            except UnicodeError:
                pass
    packets.extend(info[key] for key in ("xmp", "XML:com.adobe.xmp") if key in info)
    extension = info.get("extension")
    if image.format == "GIF" and extension and extension[0] == b"XMP DataXMP":
        # GIF XMP application extensions use a fixed magic trailer rather than
        # ordinary length-prefixed GIF data blocks. Pillow exposes their offset.
        position = image.fp.tell()
        try:
            image.fp.seek(extension[1])
            trailer = b"\x01" + bytes(range(255, -1, -1)) + b"\x00"
            data = image.fp.read(MAX_PACKET_BYTES + len(trailer))
            end = data.find(trailer)
            if end < 0:
                warnings.append("Could not read the embedded GIF XMP packet.")
            else:
                packets.append(data[:end])
        finally:
            image.fp.seek(position)
    records, individual, xmp = parse_xmp(packets, warnings)
    metadata = {"image": {key: value for key, value in info.items()
                          if key not in ("xmp", "XML:com.adobe.xmp", "exif")}}
    if exif_values:
        metadata["exif"] = exif_values
    if xmp:
        metadata["xmp"] = xmp
    return normalized_metadata(records, individual, xmp, {}, image.size, metadata, warnings)


def video_metadata(probe):
    warnings, packets, records, individual, native = [], [], [], {}, {}
    clean = json_value(probe)
    containers = [clean.get("format", {}), *clean.get("streams", [])]
    for container in containers:
        tags = container.get("tags", {})
        kept = {}
        for key, value in tags.items():
            lower = key.lower()
            if lower == "xmp":
                # Work with the original string: json_value only parses JSON.
                packets.append(value)
            elif lower == "gelbooru_metadata":
                record = _record(value, warnings)
                if record is not None:
                    records.append(record)
            elif lower.startswith("gelbooru_") and lower[9:] in FIELDS:
                field = lower[9:]
                if field == "tags" and isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except ValueError:
                        pass
                individual.setdefault(field, value)
            else:
                kept[key] = value
                native.setdefault(lower, value)
        if "tags" in container:
            container["tags"] = kept
    xmp_records, xmp_individual, xmp = parse_xmp(packets, warnings)
    records.extend(xmp_records)
    for field, value in xmp_individual.items():
        individual.setdefault(field, value)
    video = next((stream for stream in clean.get("streams", [])
                  if stream.get("codec_type") == "video" and not stream.get("disposition", {}).get("attached_pic")), {})
    dimensions = (video.get("width"), video.get("height"))
    metadata = {"format": clean.get("format", {}), "streams": clean.get("streams", [])}
    if xmp:
        metadata["xmp"] = xmp
    return normalized_metadata(records, individual, xmp, native, dimensions, metadata, warnings)
