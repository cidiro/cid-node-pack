import json
from ast import literal_eval
from ..utils.json_path import set_json_path_value
from ..utils.json_utils import parse_json_data

class CidJsonAdd:
    """
    A node to add a key/value pair to a JSON string.
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
            raise ValueError("Input 'key' is empty. Please provide a key to add.")

        # Parse the base object, tolerating common LLM formatting issues
        # (markdown fences, prose around the JSON, unescaped newlines, ...).
        try:
            data = parse_json_data(json_str or "{}", input_name="json_str")
        except ValueError as e:
            # The input could not be recovered as JSON (for example an LLM
            # reply that is plain prose). Keep the workflow running by
            # starting from an empty object instead of failing the prompt.
            reason = str(e).splitlines()[0]
            print(f"[CidJsonAdd] Warning: {reason}. Continuing with an empty object.")
            data = {}

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
        
        set_json_path_value(data, key, parsed_value)

        return (json.dumps(data, indent=4),) 
