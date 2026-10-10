import os

import numpy as np
from PIL import Image
import torch


class CidLoadImageFromPath:
    """Load a single image from a filesystem path."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_path": ("STRING", {
                    "default": "",
                    "tooltip": "Image file path, absolute or relative to ComfyUI's working directory.",
                }),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/IO"

    @classmethod
    def IS_CHANGED(cls, image_path):
        if not image_path or not image_path.strip():
            return float("nan")
        try:
            stat = os.stat(image_path)
        except OSError:
            return float("nan")
        return (os.path.abspath(image_path), stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size)

    def main(self, image_path):
        if not image_path or not image_path.strip():
            raise ValueError("Image path cannot be empty.")
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"Image file not found: '{image_path}'")

        try:
            with Image.open(image_path) as source:
                pixels = np.array(source.convert("RGB"), dtype=np.float32) / 255.0
        except OSError as exc:
            raise RuntimeError(f"Failed to load image '{image_path}': {exc}") from exc

        return (torch.from_numpy(pixels).unsqueeze(0),)
