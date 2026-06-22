import os
import subprocess

import folder_paths

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


def run_ffprobe(full_file_path):
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        full_file_path,
    ]

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
]

