import json
from ..utils.json_utils import extract_json_from_string, format_json_error

class CidArrayLength:
    """
    A node that parses a JSON string and returns the length of the array it contains.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json_str": ("STRING", {"forceInput": True, "default": "[]"}),
            },
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("length",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/JSON"

    def main(self, json_str):
        if not json_str:
            raise ValueError("Input 'json_str' is empty. Please provide a valid JSON string.")

        # Attempt to clean up common LLM markdown formatting if present
        cleaned_json_str = extract_json_from_string(json_str)

        try:
            data = json.loads(cleaned_json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"In 'json_str': {format_json_error(cleaned_json_str, e)}") from e

        if not isinstance(data, list):
            raise TypeError("The parsed JSON from 'json_str' is not an array (list).")

        return (len(data),)
