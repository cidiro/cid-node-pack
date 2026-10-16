import json
import yaml
from ..utils.json_utils import extract_json_from_string, format_json_error

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

        cleaned_json_str = extract_json_from_string(json_str)

        try:
            data = json.loads(cleaned_json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"In 'json_str': {format_json_error(cleaned_json_str, e)}") from e

        yaml_str = yaml.safe_dump(
            data,
            default_flow_style=False,
            sort_keys=False,
            width=2**31 - 1,
        )
        return (yaml_str,)
