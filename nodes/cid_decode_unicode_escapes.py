import re


_UNICODE_ESCAPE = re.compile(
    r"\\\\"
    r"|\\u(?P<high>[dD][89a-bA-B][0-9a-fA-F]{2})"
    r"\\u(?P<low>[dD][c-fC-F][0-9a-fA-F]{2})"
    r"|\\(?P<scalar>u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8})"
)


class CidDecodeUnicodeEscapes:
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("string",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/String"
    DESCRIPTION = r"Decodes numeric Unicode escapes such as \u00e9 and \U0001F600."

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
        return (_UNICODE_ESCAPE.sub(self._decode_match, string),)

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

        return match[0]
