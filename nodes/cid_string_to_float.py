class CidStringToFloat:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string": (
                    "STRING",
                    {"default": "", "multiline": False, "tooltip": "String to convert to a float"},
                ),
            }
        }

    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("float",)
    OUTPUT_TOOLTIPS = ("The parsed floating point value.",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/String"
    DESCRIPTION = "Parses a string into a floating point value. An empty string parses as 0.0."

    def main(self, string):
        return (self._parse(string),)

    def _parse(self, string):
        text = string.strip() if isinstance(string, str) else str(string).strip()
        if not text:
            return 0.0
        try:
            return float(text)
        except ValueError:
            raise ValueError(f"String to Float: cannot parse {string!r} as a float")
