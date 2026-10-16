import json
from ..utils.json_path import remove_json_path_value
from ..utils.json_utils import parse_json_data

class CidJsonRemove:
    """
    A node to remove a key/value pair from a JSON string.
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
    RETURN_NAMES = ("json_str",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/JSON"

    def main(self, json_str, key):
        if not key:
            raise ValueError("Input 'key' is empty. Please provide a key to remove.")

        if not json_str:
            return ("{}",)

        # Parse the input, tolerating common LLM formatting issues
        # (markdown fences, prose around the JSON, unescaped newlines, ...).
        data = parse_json_data(json_str, input_name="json_str")

        if not isinstance(data, dict):
            raise TypeError("The parsed JSON from 'json_str' is not an object (dictionary).")

        remove_json_path_value(data, key)

        return (json.dumps(data, indent=4),)
