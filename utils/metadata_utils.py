import json
import os
import subprocess

from PIL import Image

import folder_paths

from .structured_metadata import image_metadata, video_metadata

OUTPUT_MODES = ("normalized", "raw")


def validate_output_mode(output_mode):
    if output_mode not in OUTPUT_MODES:
        raise ValueError(f"Unsupported output_mode '{output_mode}'. Supported: {', '.join(OUTPUT_MODES)}")


def read_image_metadata(full_file_path, output_mode="normalized"):
    validate_output_mode(output_mode)
    try:
        with Image.open(full_file_path) as image:
            metadata = dict(image.info or {}) if output_mode == "raw" else image_metadata(image)
    except Exception as exc:
        raise RuntimeError(f"Failed to read metadata from '{full_file_path}': {exc}") from exc
    return json.dumps(metadata, ensure_ascii=False, default=str, indent=2, allow_nan=output_mode == "raw")


def read_video_metadata(full_file_path, output_mode="normalized"):
    validate_output_mode(output_mode)
    ffprobe_output = run_ffprobe(full_file_path, export_xmp=output_mode == "normalized")
    try:
        metadata = json.loads(ffprobe_output)
    except json.JSONDecodeError as exc:
        raise ValueError(f"ffprobe returned invalid JSON for '{full_file_path}'.") from exc
    if output_mode == "normalized":
        metadata = video_metadata(metadata)
    return json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=output_mode == "raw")


IMAGE_EXTENSIONS = {
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}

AUDIO_EXTENSIONS = {
    ".flac",
    ".mp3",
    ".wav",
}

VIDEO_EXTENSIONS = {
    ".mkv",
    ".mp4",
    ".webm",
}


def resolve_comfy_file_path(file_path):
    if not file_path:
        return None

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


def run_ffprobe(full_file_path, export_xmp=False):
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
    ]
    if export_xmp and os.path.splitext(full_file_path)[1].lower() == ".mp4":
        command.extend(["-export_xmp", "1"])
    command.append(full_file_path)

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ffprobe is required but was not found in PATH.") from exc

    if result.returncode != 0:
        stderr = result.stderr.strip() or "Unknown ffprobe error."
        raise RuntimeError(f"ffprobe failed: {stderr}")

    return result.stdout


__all__ = [
    "IMAGE_EXTENSIONS",
    "AUDIO_EXTENSIONS",
    "VIDEO_EXTENSIONS",
    "resolve_comfy_file_path",
    "run_ffprobe",
    "OUTPUT_MODES",
    "read_image_metadata",
    "read_video_metadata",
    "validate_output_mode",
]

