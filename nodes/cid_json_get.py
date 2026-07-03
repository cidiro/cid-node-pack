import json
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

    def _get_value(self, data, key):
        if key in data:
            return data[key]

        segments = key.split("/")
        if any(segment == "" for segment in segments):
            raise ValueError(f"Input 'key' contains an empty path segment: '{key}'.")

        current = data
        traversed = []

        for segment in segments:
            path = "/".join(traversed + [segment])

            if isinstance(current, dict):
                if segment not in current:
                    raise KeyError(
                        f"The key path '{key}' could not be resolved at '{path}'. "
                        f"Available keys: {list(current.keys())}"
                    )
                current = current[segment]
            elif isinstance(current, list):
                if not segment.isdigit():
                    raise TypeError(
                        f"The key path '{key}' expected a non-negative list index at '{path}', "
                        f"but got '{segment}'."
                    )

                index = int(segment)
                if index >= len(current):
                    raise IndexError(
                        f"The key path '{key}' has list index {index} out of range at '{path}'. "
                        f"List length: {len(current)}"
                    )
                current = current[index]
            else:
                raise TypeError(
                    f"The key path '{key}' could not continue at '{path}' because "
                    f"'{('/'.join(traversed))}' is a {type(current).__name__}, not an object or list."
                )

            traversed.append(segment)

        return current

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

        value = self._get_value(data, key)

        if isinstance(value, (dict, list)):
            return (json.dumps(value),)
        
        return (str(value),)
