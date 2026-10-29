"""Terminal image tournament: Python prepares previews; the browser owns voting."""
import hashlib
from pathlib import Path
import uuid

import numpy as np
from PIL import Image
import torch
import folder_paths


def flatten_images(value, path=()):
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from flatten_images(item, path + (index,))
    elif isinstance(value, torch.Tensor):
        if value.ndim != 4 or value.shape[-1] not in (1, 3, 4):
            raise ValueError("IMAGES expects BHWC image tensors with 1, 3 or 4 channels")
        if min(value.shape) < 1 or not torch.isfinite(value).all():
            raise ValueError("IMAGES contains empty dimensions or non-finite pixels")
        for index, image in enumerate(value):
            yield path + (index,), image
    else:
        raise ValueError("IMAGES expects an image batch or a list of image batches")


class CidImageABTesting:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"images": ("IMAGE", {"forceInput": True}),
                             "max_votes": ("INT", {"default": 30, "min": 1, "max": 100000})}}

    INPUT_IS_LIST = True
    OUTPUT_NODE = True
    RETURN_TYPES = ()
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Image"
    DESCRIPTION = "Compare all image pairs, confirm your preference, and preview the winner. Voting happens after execution."

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def main(self, images, max_votes):
        session_id = uuid.uuid4().hex
        candidates = list(flatten_images(images))
        if not candidates:
            raise ValueError("IMAGES must contain at least one image")
        subfolder = f"cid_ab_testing/{session_id}"
        directory = Path(folder_paths.get_temp_directory()) / subfolder
        directory.mkdir(parents=True, exist_ok=True)
        manifest = []
        for index, (source, tensor) in enumerate(candidates):
            pixels = np.clip(tensor.detach().cpu().float().numpy() * 255, 0, 255).astype(np.uint8)
            fingerprint = hashlib.sha256(str(pixels.shape).encode() + pixels.tobytes()).hexdigest()
            filename = f"{index}.png"
            Image.fromarray(pixels[:, :, 0] if pixels.shape[-1] == 1 else pixels).save(directory / filename)
            manifest.append({"id": f"{fingerprint}:{index}", "fingerprint": fingerprint,
                             "source": list(source), "width": pixels.shape[1], "height": pixels.shape[0],
                             "preview": {"filename": filename, "subfolder": subfolder, "type": "temp"}})
        budget = max_votes[0] if isinstance(max_votes, (list, tuple)) else max_votes
        return {"ui": {"cid_ab": [{"id": session_id, "images": manifest, "budget": int(budget)}]}, "result": ()}
