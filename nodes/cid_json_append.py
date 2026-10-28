import json
from ast import literal_eval
from ..utils.json_path import append_json_path_value
from ..utils.json_utils import extract_json_from_string, format_json_error

class CidJsonAppend:
    """
    A node to append a value to a JSON list by key or slash-delimited path.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "key": ("STRING", {"default": ""}),
                "value": ("STRING", {"default": ""}),
            },
            "optional": {
                "json_str": ("STRING", {"forceInput": True, "default": "{}"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("json_str",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/JSON"

    def main(self, key, value, json_str="{}"):
        if not key:
            raise ValueError("Input 'key' is empty. Please provide a key to append to.")

        # Attempt to clean up common LLM markdown formatting if present
        cleaned_json_str = extract_json_from_string(json_str) if json_str else "{}"

        try:
            data = json.loads(cleaned_json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"In 'json_str': {format_json_error(cleaned_json_str, e)}") from e

        if not isinstance(data, dict):
            raise TypeError("The parsed JSON from 'json_str' is not an object (dictionary).")

        parsed_value = value
        try:
            # Try to parse the value as a JSON literal (e.g., a number, boolean, array, or object)
            parsed_value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            # If it fails, it might be a Python literal string, so we try to evaluate it safely
            try:
                parsed_value = literal_eval(value)
            except (ValueError, SyntaxError, MemoryError):
                # If it still fails, treat it as a plain string
                pass

        append_json_path_value(data, key, parsed_value)

        return (json.dumps(data, indent=2),)
