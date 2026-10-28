import json
from ..utils.json_path import get_json_path_value
from ..utils.json_utils import extract_json_from_string, format_json_error

class CidJsonGet:
    """
    A node to get a value from a JSON string by key or slash-delimited path.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json_str": ("STRING", {"forceInput": True, "default": "{}"}),
                "key": ("STRING", {"default": ""}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("value",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/JSON"

    def main(self, json_str, key):
        if not json_str:
            raise ValueError("Input 'json_str' is empty. Please provide a valid JSON string.")

        # Attempt to clean up common LLM markdown formatting if present
        cleaned_json_str = extract_json_from_string(json_str)

        try:
            data = json.loads(cleaned_json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"In 'json_str': {format_json_error(cleaned_json_str, e)}") from e

        if not isinstance(data, dict):
            raise TypeError("The parsed JSON from 'json_str' is not an object (dictionary).")

        value = get_json_path_value(data, key)

        if isinstance(value, (dict, list)):
            return (json.dumps(value, indent=2),)
        
        return (str(value),)
