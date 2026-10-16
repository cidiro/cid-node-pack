import json
from ..utils.json_path import get_json_path_value
from ..utils.json_utils import parse_json_data

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

        # Parse the input, tolerating common LLM formatting issues
        # (markdown fences, prose around the JSON, unescaped newlines, ...).
        data = parse_json_data(json_str, input_name="json_str")

        if not isinstance(data, dict):
            raise TypeError("The parsed JSON from 'json_str' is not an object (dictionary).")

        value = get_json_path_value(data, key)

        if isinstance(value, (dict, list)):
            return (json.dumps(value),)
        
        return (str(value),)
