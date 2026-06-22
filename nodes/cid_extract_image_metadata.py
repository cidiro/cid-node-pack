import json

from PIL import Image

from ..utils.metadata_utils import resolve_comfy_file_path


class CidExtractImageMetadata:
    """
    Load an image file and return its Pillow metadata dictionary as JSON.
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
    CATEGORY = "Cid Node Pack/IO"

    def find_file(self, file_path):
        return resolve_comfy_file_path(file_path)

    def main(self, file_path):
        full_file_path = self.find_file(file_path)
        if not full_file_path:
            raise FileNotFoundError(
                f"The file '{file_path}' could not be found as an absolute path, or in the ComfyUI input/output directories."
            )

        try:
            with Image.open(full_file_path) as img:
                metadata = dict(img.info or {})
        except Exception as exc:
            raise RuntimeError(f"Failed to read metadata from '{full_file_path}': {exc}") from exc

        try:
            metadata_json = json.dumps(metadata, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            safe_metadata = {key: str(value) for key, value in metadata.items()}
            metadata_json = json.dumps(safe_metadata, ensure_ascii=False)

        return (metadata_json,)
