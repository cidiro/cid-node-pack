import json
import os
import folder_paths
from ..utils.json_utils import extract_json_from_string, format_json_error

class CidJsonSave:
    """
    A node to save a JSON string to a file.
    """
    
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json_str": ("STRING", {"forceInput": True, "default": "{}"}),
                "file_path": ("STRING",),
                "overwrite_on_collision": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ()
    OUTPUT_NODE = True
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/JSON"

    def main(self, json_str, file_path, overwrite_on_collision):
        if not json_str:
            raise ValueError("Input 'json_str' is empty. Please provide a valid JSON string.")
        
        # Attempt to clean up common LLM markdown formatting if present
        cleaned_json_str = extract_json_from_string(json_str)

        try:
            data = json.loads(cleaned_json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"In 'json_str': {format_json_error(cleaned_json_str, e)}") from e

        full_file_path = os.path.join(self.output_dir, file_path)
        directory = os.path.dirname(full_file_path)

        if not os.path.exists(directory):
            raise FileNotFoundError(f"The directory '{directory}' does not exist.")

        if os.path.exists(full_file_path) and not overwrite_on_collision:
            raise FileExistsError(f"File '{file_path}' already exists and 'overwrite_on_collision' is False.")

        with open(full_file_path, 'w') as f:
            json.dump(data, f, indent=4)

        return {}
