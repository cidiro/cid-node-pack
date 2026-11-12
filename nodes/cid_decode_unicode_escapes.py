import re
from html import unescape
from html.entities import html5


_ESCAPE = re.compile(
    r"\\\\"
    r"|\\u(?P<high>[dD][89a-bA-B][0-9a-fA-F]{2})"
    r"\\u(?P<low>[dD][c-fC-F][0-9a-fA-F]{2})"
    r"|\\(?P<scalar>u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8})"
    r"|&(?P<numeric>#[0-9]+|#[xX][0-9a-fA-F]+);"
    r"|&(?P<name>[A-Za-z][A-Za-z0-9]*;)"
)


class CidDecodeUnicodeEscapes:
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("string",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/String"
    DESCRIPTION = (
        r"Decodes Unicode escapes such as \u00e9 and \U0001F600, "
        "and HTML character references such as &#039; and &amp;."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string": (
                    "STRING",
                    {"default": "", "multiline": True, "dynamicPrompts": False},
                ),
            }
        }

    def main(self, string):
        return (_ESCAPE.sub(self._decode_match, string),)

    @staticmethod
    def _decode_match(match):
        if match["high"] is not None:
            high = int(match["high"], 16) - 0xD800
            low = int(match["low"], 16) - 0xDC00
            return chr(0x10000 + (high << 10) + low)

        scalar = match["scalar"]
        if scalar is not None:
            code_point = int(scalar[1:], 16)
            if code_point <= 0x10FFFF and not 0xD800 <= code_point <= 0xDFFF:
                return chr(code_point)

        numeric = match["numeric"]
        if numeric is not None:
            hexadecimal = numeric[1] in "xX"
            digits = numeric[2 if hexadecimal else 1:].lstrip("0") or "0"
            if len(digits) > (6 if hexadecimal else 7):
                # The value is above U+10FFFF, even before conversion.
                return "\ufffd"
            prefix = "x" if hexadecimal else ""
            return unescape(f"&#{prefix}{digits};")

        name = match["name"]
        if name is not None:
            return html5.get(name, match[0])

        return match[0]
