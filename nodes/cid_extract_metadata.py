import json
import os

from PIL import Image

from ..utils.metadata_utils import (
    AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    resolve_comfy_file_path,
    run_ffprobe,
)


class CidExtractMetadata:
    """
    Extract metadata from images, audio, or video files and return it as JSON.
    """

    MEDIA_TYPES = ("auto", "image", "audio", "video")
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("json_str",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/IO"

    EXTENSION_MAP = {
        "image": IMAGE_EXTENSIONS,
        "audio": AUDIO_EXTENSIONS,
        "video": VIDEO_EXTENSIONS,
    }

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING",),
                "media_type": (
                    cls.MEDIA_TYPES,
                    {
                        "default": "auto",
                    },
                ),
            }
        }

    def find_file(self, file_path):
        return resolve_comfy_file_path(file_path)

    def ensure_supported_extension(self, full_file_path, media_type):
        extensions = self.EXTENSION_MAP.get(media_type)
        if not extensions:
            return

        _, ext = os.path.splitext(full_file_path)
        if ext.lower() not in extensions:
            supported = ", ".join(sorted(extensions))
            raise ValueError(
                f"Unsupported {media_type} extension '{ext}'. Supported: {supported}"
            )

    def resolve_media_type(self, full_file_path, media_type):
        normalized = (media_type or "auto").strip().lower()
        if normalized not in self.MEDIA_TYPES:
            supported = ", ".join(self.MEDIA_TYPES)
            raise ValueError(f"Unsupported media_type '{media_type}'. Supported: {supported}")

        if normalized != "auto":
            self.ensure_supported_extension(full_file_path, normalized)
            return normalized

        _, ext = os.path.splitext(full_file_path)
        lowered_ext = ext.lower()
        for media_type_name, extensions in self.EXTENSION_MAP.items():
            if lowered_ext in extensions:
                return media_type_name

        image_exts = ", ".join(sorted(IMAGE_EXTENSIONS))
        audio_exts = ", ".join(sorted(AUDIO_EXTENSIONS))
        video_exts = ", ".join(sorted(VIDEO_EXTENSIONS))
        raise ValueError(
            f"Unable to determine media type from extension '{ext}'. "
            f"Supported image extensions: {image_exts}. "
            f"Supported audio extensions: {audio_exts}. "
            f"Supported video extensions: {video_exts}."
        )

    def read_image_metadata(self, full_file_path):
        try:
            with Image.open(full_file_path) as img:
                metadata = dict(img.info or {})
        except Exception as exc:
            raise RuntimeError(f"Failed to read metadata from '{full_file_path}': {exc}") from exc

        try:
            return json.dumps(metadata, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            safe_metadata = {key: str(value) for key, value in metadata.items()}
            return json.dumps(safe_metadata, ensure_ascii=False)

    def read_av_metadata(self, full_file_path):
        ffprobe_output = run_ffprobe(full_file_path)
        try:
            metadata = json.loads(ffprobe_output)
        except json.JSONDecodeError as exc:
            raise ValueError(f"ffprobe returned invalid JSON for '{full_file_path}'.") from exc

        return json.dumps(metadata, ensure_ascii=False, indent=2)

    def main(self, file_path, media_type="auto"):
        full_file_path = self.find_file(file_path)
        if not full_file_path:
            raise FileNotFoundError(
                f"The file '{file_path}' could not be found as an absolute path, or in the ComfyUI input/output directories."
            )

        resolved_media_type = self.resolve_media_type(full_file_path, media_type)
        if resolved_media_type == "image":
            json_str = self.read_image_metadata(full_file_path)
        else:
            json_str = self.read_av_metadata(full_file_path)

        return (json_str,)

