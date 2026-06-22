import json
import os
import folder_paths
from ..utils.json_utils import extract_json_from_string, format_json_error

class CidJsonLoad:
    """
    A node to load a JSON string from a file.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING",),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("json_str",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/JSON"

    def find_file(self, file_path):
        if os.path.isabs(file_path) and os.path.exists(file_path):
            return file_path

        input_dir = folder_paths.get_input_directory()
        input_path = os.path.join(input_dir, file_path)
        if os.path.exists(input_path):
            return input_path

        output_dir = folder_paths.get_output_directory()
        output_path = os.path.join(output_dir, file_path)
        if os.path.exists(output_path):
            return output_path
        
        return None

    def main(self, file_path):
        full_file_path = self.find_file(file_path)

        if not full_file_path:
            raise FileNotFoundError(f"The file '{file_path}' could not be found as an absolute path, or in the ComfyUI input/output directories.")

        try:
            with open(full_file_path, 'r', encoding='utf-8') as f:
                json_content = f.read()

                # Attempt to clean up common LLM markdown formatting if present
                cleaned_json_content = extract_json_from_string(json_content)

                json_data = json.loads(cleaned_json_content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in file '{full_file_path}': {format_json_error(cleaned_json_content, e)}") from e
        except Exception as e:
            raise RuntimeError(f"An error occurred while reading file '{full_file_path}': {e}") from e

        return (json.dumps(json_data, indent=4),) 
