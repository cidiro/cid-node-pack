from ..utils.json_utils import parse_json_data

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

        # Parse the input, tolerating common LLM formatting issues
        # (markdown fences, prose around the JSON, unescaped newlines, ...).
        data = parse_json_data(json_str, input_name="json_str")

        if not isinstance(data, list):
            raise TypeError("The parsed JSON from 'json_str' is not an array (list).")

        return (len(data),)
