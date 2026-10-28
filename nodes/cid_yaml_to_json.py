import json
import yaml
import re

class CidYamlToJson:
    """
    A node to convert a YAML string to a JSON string.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "yaml_str": ("STRING", {"forceInput": True, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("json_str",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/JSON"

    def _clean_yaml_string(self, yaml_str):
        """
        Cleans up a string that might contain markdown formatting around YAML
        (common with LLM outputs) and returns the core YAML string.
        """
        s = yaml_str.strip()
        
        # Remove starting markdown block with optional language specifier
        s = re.sub(r"^```[a-zA-Z]*\s*\n", "", s)
        
        # Remove trailing markdown block
        if s.endswith("```"):
            s = s[:-3].strip()
            
        # If it just starts with "yaml\n"
        if s.lower().startswith("yaml\n"):
            s = s[5:].strip()
            
        return s

    def main(self, yaml_str):
        if not yaml_str:
            raise ValueError("Input 'yaml_str' is empty. Please provide a valid YAML string.")

        cleaned_yaml_str = self._clean_yaml_string(yaml_str)

        try:
            data = yaml.safe_load(cleaned_yaml_str)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML string:\n{e}\n\nFull string:\n{cleaned_yaml_str}") from e

        if data is None:
            data = {}

        json_str = json.dumps(data, indent=2)
        return (json_str,)
