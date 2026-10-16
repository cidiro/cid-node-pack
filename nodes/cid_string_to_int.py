import math


class CidStringToInt:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string": (
                    "STRING",
                    {"default": "", "multiline": False, "tooltip": "String to convert to an integer"},
                ),
                "rounding": (
                    ["round", "floor", "ceil", "truncate"],
                    {"default": "round", "tooltip": "How to reduce a parsed float to an integer"},
                ),
            }
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("int",)
    OUTPUT_TOOLTIPS = ("The parsed integer value.",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/String"
    DESCRIPTION = "Parses a string into an integer value. An empty string parses as 0."

    _ROUNDER = {
        "round": lambda value: round(value),
        "floor": lambda value: math.floor(value),
        "ceil": lambda value: math.ceil(value),
        "truncate": lambda value: math.trunc(value),
    }

    def main(self, string, rounding):
        return (self._parse(string, rounding),)

    def _parse(self, string, rounding):
        text = string.strip() if isinstance(string, str) else str(string).strip()
        if not text:
            return 0
        try:
            value = float(text)
        except ValueError:
            raise ValueError(f"String to Int: cannot parse {string!r} as a number")

        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"String to Int: {string!r} is not a finite number")

        return int(self._ROUNDER[rounding](value))
