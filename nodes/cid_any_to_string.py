import json

from ..utils import any_type


class CidAnyToString:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": (any_type, {"forceInput": True, "tooltip": "Any value to convert to a string"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("string",)
    OUTPUT_TOOLTIPS = ("The input value cast to a string.",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/String"
    DESCRIPTION = "Casts any input value to a string."

    def main(self, value):
        return (self._to_string(value),)

    def _to_string(self, value):
        if isinstance(value, str):
            return value

        # Containers render as JSON when possible; fall back to str() for
        # values JSON cannot represent.
        if isinstance(value, (dict, list, tuple)):
            try:
                return json.dumps(value, default=str, indent=2)
            except (TypeError, ValueError):
                return str(value)

        # Tensor-like values (IMAGE, MASK, LATENT, ...) would stringify to
        # megabytes of numbers, so describe them instead.
        if hasattr(value, "shape") and hasattr(value, "dtype"):
            return f"{type(value).__name__}(shape={tuple(value.shape)}, dtype={value.dtype})"

        return str(value)
