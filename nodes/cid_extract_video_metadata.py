import os

from ..utils.metadata_utils import OUTPUT_MODES, VIDEO_EXTENSIONS, read_video_metadata, resolve_comfy_file_path


class CidExtractVideoMetadata:
    """
    Extract metadata from supported video files using ffprobe and return it as JSON.
    """

    SUPPORTED_EXTENSIONS = VIDEO_EXTENSIONS

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

    def ensure_supported_extension(self, file_path):
        _, ext = os.path.splitext(file_path)
        if ext.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported video extension '{ext}'. Supported: {', '.join(sorted(self.SUPPORTED_EXTENSIONS))}"
            )

    def main(self, file_path, output_mode="normalized"):
        full_file_path = self.find_file(file_path)
        if not full_file_path:
            raise FileNotFoundError(
                f"The file '{file_path}' could not be found as an absolute path, or in the ComfyUI input/output directories."
            )

        self.ensure_supported_extension(full_file_path)

        return (read_video_metadata(full_file_path, output_mode),)
