"""Exercise the public node output, including real image metadata packets."""

import importlib
import json
from pathlib import Path
import sys
import types
import xml.etree.ElementTree as ET

import pytest
from PIL import Image, PngImagePlugin


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "cid_metadata_test"
for suffix, path in (("", ROOT), (".nodes", ROOT / "nodes"), (".utils", ROOT / "utils")):
    package = types.ModuleType(PACKAGE + suffix)
    package.__path__ = [str(path)]
    sys.modules[PACKAGE + suffix] = package
original_paths = sys.modules.get("folder_paths")
stub_paths = types.ModuleType("folder_paths")
stub_paths.get_input_directory = lambda: "/unused-test-input"
stub_paths.get_output_directory = lambda: "/unused-test-output"
sys.modules["folder_paths"] = stub_paths
try:
    utils = importlib.import_module(PACKAGE + ".utils.metadata_utils")
    structured = importlib.import_module(PACKAGE + ".utils.structured_metadata")
    node_module = importlib.import_module(PACKAGE + ".nodes.cid_extract_metadata")
    image_node = importlib.import_module(PACKAGE + ".nodes.cid_extract_image_metadata")
    video_node = importlib.import_module(PACKAGE + ".nodes.cid_extract_video_metadata")
    json_get = importlib.import_module(PACKAGE + ".nodes.cid_json_get").CidJsonGet()
finally:
    if original_paths is None:
        del sys.modules["folder_paths"]
    else:
        sys.modules["folder_paths"] = original_paths


TAGS = "1girl bare_shoulders breasts brown_hair character_name collar commentary_request dated female_focus gloves green_eyes hairband headgear highres kantai_collection large_breasts murano_machi mutsu_(kancolle) mutsu_kai_ni_(kancolle) pink_background pink_lips radio_antenna short_hair solo twitter_username upper_body white_gloves".split()


def record(**changes):
    return {
        "schema_version": 2, "site": "gelbooru.com", "post_id": 4632336,
        "post_url": "https://gelbooru.com/index.php?page=post&s=view&id=4632336",
        "tags": TAGS, "width": 1091, "height": 1440, "original_width": 1091, "original_height": 1440,
        "maximum_megapixels": 2.0, "rating": "questionable", "resized": False, "score": 1,
        "source_md5": "0202e63eae0dcfdb7b2c3c705856a56d",
        "source_url": "https://twitter.com/bbmm145/status/1101863331596398593",
        "uploaded_at": "2019-03-03T04:30:22Z", "uploaded_at_raw": "Sat Mar 02 22:30:22 -0600 2019",
        "uploader_id": 6498, "uploader_name": "danbooru", **changes,
    }


def packet(post=None, individual=None):
    root = ET.Element("{adobe:ns:meta/}xmpmeta")
    rdf = ET.SubElement(root, f"{{{structured.RDF}}}RDF")
    description = ET.SubElement(rdf, f"{{{structured.RDF}}}Description")
    alt = ET.SubElement(ET.SubElement(description, f"{{{structured.DC}}}description"), f"{{{structured.RDF}}}Alt")
    ET.SubElement(alt, f"{{{structured.RDF}}}li", {"{http://www.w3.org/XML/1998/namespace}lang": "x-default"}).text = "Original caption & attribution"
    ET.SubElement(alt, f"{{{structured.RDF}}}li", {"{http://www.w3.org/XML/1998/namespace}lang": "de"}).text = "Beschreibung"
    bag = ET.SubElement(ET.SubElement(description, f"{{{structured.DC}}}subject"), f"{{{structured.RDF}}}Bag")
    ET.SubElement(bag, f"{{{structured.RDF}}}li").text = "source_keyword"
    if post is not None:
        ET.SubElement(description, f"{{{structured.GBRD}}}Record").text = json.dumps(post, ensure_ascii=False) if isinstance(post, dict) else post
    for key, value in (individual or {}).items():
        element = ET.SubElement(description, f"{{{structured.GBRD}}}{key}")
        if isinstance(value, list):
            bag = ET.SubElement(element, f"{{{structured.RDF}}}Bag")
            for item in value:
                ET.SubElement(bag, f"{{{structured.RDF}}}li").text = item
        else:
            element.text = str(value)
    return ET.tostring(root, encoding="utf-8")


def save_image(path, xmp=None, size=(1091, 1440), **options):
    with Image.new("RGB", size, (30, 80, 120)) as image:
        if path.suffix == ".png":
            info = PngImagePlugin.PngInfo()
            if xmp is not None:
                info.add_itxt("XML:com.adobe.xmp", xmp.decode())
            info.add_text("prompt", '{"1":{"class_type":"Example"}}')
            info.add_text("workflow", '{"nodes":[]}')
            info.add_text("plain_text", "1.20")
            image.save(path, pnginfo=info, **options)
        elif path.suffix == ".jpg":
            image.save(path, **options)
            if xmp is not None:
                # JPEG APP1 XMP works on older Pillow encoders too.
                data = path.read_bytes()
                segment = b"http://ns.adobe.com/xap/1.0/\x00" + xmp
                path.write_bytes(data[:2] + b"\xff\xe1" + (len(segment) + 2).to_bytes(2, "big") + segment + data[2:])
        elif path.suffix == ".gif":
            image.save(path, **options)
            if xmp is not None:
                data = path.read_bytes()
                start = 13 + (3 * 2 ** ((data[10] & 7) + 1) if data[10] & 128 else 0)
                trailer = b"\x01" + bytes(range(255, -1, -1)) + b"\x00"
                path.write_bytes(data[:start] + b"!\xff\x0bXMP DataXMP" + xmp + trailer + data[start:])
        else:
            image.save(path, xmp=xmp, **options)


@pytest.mark.parametrize("extension", ["jpg", "png", "webp", "gif"])
def test_sample_is_top_level_typed_json(tmp_path, extension):
    path = tmp_path / ("sample." + extension)
    post = record()
    save_image(path, packet(post))
    output = node_module.CidExtractMetadata().main(str(path))[0]
    result = json.loads(output)
    for key, value in post.items():
        assert result[key] == value
        assert type(result[key]) is type(value)
    assert result["metadata"]["gelbooru_schema_version"] == 2
    assert "gbrd:Record" not in result["metadata"].get("xmp", {})
    assert result["metadata"]["xmp"]["dc:description"]["de"] == "Beschreibung"
    assert "<?xpacket" not in output and "<rdf:" not in output and '"xmp": "b' not in output
    assert json_get.main(output, "tags") == (json.dumps(TAGS, indent=2),)
    assert json_get.main(output, "width") == ("1091",)
    assert json_get.main(output, "uploaded_at") == ("2019-03-03T04:30:22Z",)
    assert json.loads(image_node.CidExtractImageMetadata().main(str(path))[0]) == result


def test_actual_dimensions_override_stale_record_and_empty_values_survive(tmp_path):
    path = tmp_path / "small.png"
    save_image(path, packet(record(tags=[], score=0, title="false", uploader_name="1.20")), size=(8, 6))
    result = json.loads(node_module.CidExtractMetadata().main(str(path))[0])
    assert (result["width"], result["height"]) == (8, 6)
    assert result["original_width"] == 1091
    assert result["tags"] == [] and result["score"] == 0 and result["resized"] is False
    assert result["title"] == "false" and result["uploader_name"] == "1.20"
    assert result["metadata"]["image"]["prompt"] == {"1": {"class_type": "Example"}}
    assert result["metadata"]["image"]["workflow"] == {"nodes": []}
    assert result["metadata"]["image"]["plain_text"] == "1.20"


def test_v1_record_is_normalized(tmp_path):
    path = tmp_path / "old.png"
    post = record(schema_version=1, uploaded_at="Sat Mar 02 22:30:22 -0600 2019")
    for key in ("width", "height", "original_width", "original_height", "uploaded_at_raw"):
        post.pop(key)
    post.update(saved_dimensions={"width": 1091, "height": 1440}, original_dimensions={"width": 2182, "height": 2880})
    save_image(path, packet(post))
    result = json.loads(node_module.CidExtractMetadata().main(str(path))[0])
    assert result["schema_version"] == 2
    assert result["metadata"]["gelbooru_schema_version"] == 1
    assert result["original_width"] == 2182 and result["original_height"] == 2880
    assert result["uploaded_at"] == "2019-03-03T04:30:22Z"
    assert result["uploaded_at_raw"] == post["uploaded_at"]
    assert "saved_dimensions" not in result and "original_dimensions" not in result


@pytest.mark.parametrize("bad_record", ["not JSON", "[]", '{"schema_version":99}', '{"schema_version":true}'])
def test_bad_record_falls_back_to_individual_fields(tmp_path, bad_record):
    path = tmp_path / "bad.png"
    fields = {"SchemaVersion": "2", "Tags": ["unicode_é", "<>&\"'", "true"], "Score": "0",
              "Resized": "False", "UploadedAt": "2019-03-02T22:30:22-06:00", "PostId": "4632336"}
    save_image(path, packet(bad_record, fields))
    result = json.loads(node_module.CidExtractMetadata().main(str(path))[0])
    assert result["post_id"] == 4632336 and result["score"] == 0 and result["resized"] is False
    assert result["tags"] == sorted(fields["Tags"])
    assert result["uploaded_at"] == "2019-03-03T04:30:22Z"
    assert result["metadata"]["warnings"]


def test_record_precedes_individual_then_standard_fields(tmp_path):
    path = tmp_path / "priorities.png"
    post = record(score="invalid", tags=["true", "1.20", '{"a":1}'])
    post.pop("title", None)
    save_image(path, packet(post, {"Tags": ["other"], "Score": "-2", "Title": "Individual title"}))
    result = json.loads(node_module.CidExtractMetadata().main(str(path))[0])
    assert result["tags"] == sorted(post["tags"])
    assert result["score"] == -2 and result["title"] == "Individual title"
    assert result["description"] == "Original caption & attribution"


def test_duplicate_packets_do_not_duplicate_results_or_warnings():
    text = packet(record())
    warnings = []
    records, fields, remaining = structured.parse_xmp([text, text.decode()], warnings)
    assert len(records) == 1 and not warnings and not fields
    assert remaining["dc:subject"] == ["source_keyword"]


@pytest.mark.parametrize("bad_xml", [b"not xml", b'<!DOCTYPE a [<!ENTITY e "expansion">]><a>&e;</a>'])
def test_bad_xml_does_not_break_image_extraction(tmp_path, bad_xml):
    path = tmp_path / "broken.png"
    save_image(path, bad_xml, size=(8, 6))
    result = json.loads(node_module.CidExtractMetadata().main(str(path))[0])
    assert (result["width"], result["height"]) == (8, 6)
    assert result["metadata"]["warnings"]


def test_no_record_standard_metadata_and_binary_summaries(tmp_path):
    path = tmp_path / "plain.png"
    exif = Image.Exif()
    exif[315] = "Actual artist"
    save_image(path, packet(), size=(8, 6), exif=exif, icc_profile=b"profile bytes")
    result = json.loads(node_module.CidExtractMetadata().main(str(path))[0])
    assert result["tags"] == ["source_keyword"]
    assert "schema_version" not in result
    assert result["metadata"]["exif"]["Artist"] == "Actual artist"
    assert result["metadata"]["image"]["icc_profile"] == {"byte_length": 13}


def test_raw_mode_is_previous_pillow_output(tmp_path):
    path = tmp_path / "raw.jpg"
    save_image(path, packet(record()))
    with Image.open(path) as image:
        expected = json.loads(json.dumps(dict(image.info), default=str))
    assert json.loads(node_module.CidExtractMetadata().main(str(path), output_mode="raw")[0]) == expected


@pytest.mark.parametrize("uploaded_at", ["unknown date", "2019-03-03T04:30:22"])
def test_unknown_or_naive_date_keeps_only_raw_time(tmp_path, uploaded_at):
    path = tmp_path / "date.png"
    save_image(path, packet(record(uploaded_at=uploaded_at, uploaded_at_raw=uploaded_at)))
    result = json.loads(node_module.CidExtractMetadata().main(str(path))[0])
    assert "uploaded_at" not in result and result["uploaded_at_raw"] == uploaded_at


@pytest.mark.parametrize("extension", ["mp4", "webm"])
def test_video_nodes_and_xmp_export_flag(tmp_path, monkeypatch, extension):
    path = tmp_path / ("clip." + extension)
    path.touch()
    post = record()
    tags = {"title": "Native title", "comment": "Source comment"}
    if extension == "mp4":
        tags["xmp"] = packet(post).decode()
    else:
        tags["GELBOORU_METADATA"] = json.dumps(post)
        tags["GELBOORU_TAGS"] = json.dumps(TAGS)
        tags["GELBOORU_RESIZED"] = "false"
    probe = {"format": {"tags": tags}, "streams": [{"codec_type": "video", "width": 1091, "height": 1440}]}
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        return types.SimpleNamespace(returncode=0, stdout=json.dumps(probe), stderr="")
    monkeypatch.setattr(utils.subprocess, "run", run)
    output = node_module.CidExtractMetadata().main(str(path))[0]
    result = json.loads(output)
    assert all(result[key] == value for key, value in post.items())
    assert result["metadata"]["format"]["tags"] == {"title": "Native title", "comment": "Source comment"}
    assert ("-export_xmp" in calls[-1]) is (extension == "mp4")
    assert json.loads(video_node.CidExtractVideoMetadata().main(str(path))[0]) == result
    assert json.loads(node_module.CidExtractMetadata().main(str(path), output_mode="raw")[0]) == probe
    assert "-export_xmp" not in calls[-1]


def test_webm_individual_fields_fallback():
    probe = {"format": {"tags": {"gelbooru_metadata": "broken", "GELBOORU_TAGS": '["sky"]',
                                "GELBOORU_SCORE": "0", "GELBOORU_RESIZED": "false"}},
             "streams": [{"codec_type": "video", "width": 20, "height": 10}]}
    result = structured.video_metadata(probe)
    assert result["tags"] == ["sky"] and result["score"] == 0 and result["resized"] is False
    assert result["metadata"]["warnings"]


def test_audio_output_is_unchanged(tmp_path, monkeypatch):
    path = tmp_path / "sound.wav"
    path.touch()
    probe = {"format": {"tags": {"title": "Track"}}, "streams": [{"codec_type": "audio"}]}
    monkeypatch.setattr(node_module, "run_ffprobe", lambda path: json.dumps(probe))
    assert json.loads(node_module.CidExtractMetadata().main(str(path))[0]) == probe


def test_missing_files_and_invalid_modes(tmp_path):
    node = node_module.CidExtractMetadata()
    with pytest.raises(FileNotFoundError):
        node.main(str(tmp_path / "missing.png"))
    with pytest.raises(ValueError, match="output_mode"):
        node.main("unused", output_mode="invalid")
    assert node.INPUT_TYPES()["optional"]["output_mode"][1]["default"] == "normalized"
