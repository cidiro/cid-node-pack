import json
import os

from ..utils.metadata_utils import (
    AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    OUTPUT_MODES,
    read_image_metadata,
    read_video_metadata,
    resolve_comfy_file_path,
    run_ffprobe,
    validate_output_mode,
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
            },
            "optional": {"output_mode": (OUTPUT_MODES, {"default": "normalized"})},
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

    def read_image_metadata(self, full_file_path, output_mode="normalized"):
        return read_image_metadata(full_file_path, output_mode)

    def read_av_metadata(self, full_file_path, output_mode="normalized", media_type=None):
        if (media_type or self.resolve_media_type(full_file_path, "auto")) == "video":
            return read_video_metadata(full_file_path, output_mode)
        ffprobe_output = run_ffprobe(full_file_path)
        try:
            metadata = json.loads(ffprobe_output)
        except json.JSONDecodeError as exc:
            raise ValueError(f"ffprobe returned invalid JSON for '{full_file_path}'.") from exc

        return json.dumps(metadata, ensure_ascii=False, indent=2)

    def main(self, file_path, media_type="auto", output_mode="normalized"):
        validate_output_mode(output_mode)
        full_file_path = self.find_file(file_path)
        if not full_file_path:
            raise FileNotFoundError(
                f"The file '{file_path}' could not be found as an absolute path, or in the ComfyUI input/output directories."
            )

        resolved_media_type = self.resolve_media_type(full_file_path, media_type)
        if resolved_media_type == "image":
            json_str = self.read_image_metadata(full_file_path, output_mode)
        else:
            json_str = self.read_av_metadata(full_file_path, output_mode, resolved_media_type)

        return (json_str,)

