from ..utils.metadata_utils import OUTPUT_MODES, read_image_metadata, resolve_comfy_file_path


class CidExtractImageMetadata:
    """
    Load an image file and return normalized metadata as JSON.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING",),
            },
            "optional": {"output_mode": (OUTPUT_MODES, {"default": "normalized"})},
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("json_str",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/IO"

    def find_file(self, file_path):
        return resolve_comfy_file_path(file_path)

    def main(self, file_path, output_mode="normalized"):
        full_file_path = self.find_file(file_path)
        if not full_file_path:
            raise FileNotFoundError(
                f"The file '{file_path}' could not be found as an absolute path, or in the ComfyUI input/output directories."
            )

        return (read_image_metadata(full_file_path, output_mode),)
