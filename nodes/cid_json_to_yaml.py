import yaml
from ..utils.json_utils import parse_json_data

class CidJsonToYaml:
    """
    A node to convert a JSON string to a YAML string.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json_str": ("STRING", {"forceInput": True, "default": "{}"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("yaml_str",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/JSON"

    def main(self, json_str):
        if not json_str:
            raise ValueError("Input 'json_str' is empty. Please provide a valid JSON string.")

        # Parse the input, tolerating common LLM formatting issues
        # (markdown fences, prose around the JSON, unescaped newlines, ...).
        data = parse_json_data(json_str, input_name="json_str")

        yaml_str = yaml.safe_dump(
            data,
            default_flow_style=False,
            sort_keys=False,
            width=2**31 - 1,
        )
        return (yaml_str,)
