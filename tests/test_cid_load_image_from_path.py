import importlib.util
import os
from pathlib import Path

import pytest

pytest.importorskip("torch", reason="torch is only available in the ComfyUI environment")
import torch
from PIL import Image


spec = importlib.util.spec_from_file_location(
    "cid_load_image_from_path",
    Path(__file__).resolve().parents[1] / "nodes" / "cid_load_image_from_path.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
CidLoadImageFromPath = module.CidLoadImageFromPath


@pytest.mark.parametrize("mode,color,expected", [
    ("RGB", (255, 128, 0), [1.0, 128 / 255, 0.0]),
    ("RGBA", (255, 128, 0, 0), [1.0, 128 / 255, 0.0]),
    ("L", 128, [128 / 255] * 3),
])
def test_loads_rgb_tensor(tmp_path, mode, color, expected):
    path = tmp_path / "image.png"
    Image.new(mode, (3, 2), color).save(path)

    result = CidLoadImageFromPath().main(str(path))

    assert len(result) == 1
    image = result[0]
    assert image.shape == (1, 2, 3, 3)
    assert image.dtype == torch.float32
    torch.testing.assert_close(image, torch.tensor(expected).expand(1, 2, 3, 3))


def test_relative_path(tmp_path, monkeypatch):
    Image.new("RGB", (1, 1)).save(tmp_path / "image.png")
    monkeypatch.chdir(tmp_path)
    assert CidLoadImageFromPath().main("image.png")[0].shape == (1, 1, 1, 3)


def test_loads_first_animation_frame(tmp_path):
    path = tmp_path / "image.gif"
    Image.new("RGB", (2, 2), "red").save(
        path, save_all=True, append_images=[Image.new("RGB", (2, 2), "blue")]
    )
    image = CidLoadImageFromPath().main(str(path))[0]
    torch.testing.assert_close(image, torch.tensor([1.0, 0.0, 0.0]).expand(1, 2, 2, 3))


@pytest.mark.parametrize("path", ["", "   "])
def test_empty_path(path):
    with pytest.raises(ValueError, match="cannot be empty"):
        CidLoadImageFromPath().main(path)


def test_missing_path(tmp_path):
    with pytest.raises(FileNotFoundError, match="Image file not found"):
        CidLoadImageFromPath().main(str(tmp_path / "missing.png"))


def test_invalid_image(tmp_path):
    path = tmp_path / "invalid.png"
    path.write_text("not an image")
    with pytest.raises(RuntimeError, match="Failed to load image"):
        CidLoadImageFromPath().main(str(path))


def test_refresh_after_file_replacement(tmp_path):
    path = tmp_path / "image.png"
    Image.new("RGB", (2, 2), "red").save(path)
    before = CidLoadImageFromPath.IS_CHANGED(str(path))
    Image.new("RGB", (2, 2), "blue").save(path)
    os.utime(path, ns=(before[1] + 1_000_000, before[1] + 1_000_000))
    assert CidLoadImageFromPath.IS_CHANGED(str(path)) != before
    image = CidLoadImageFromPath().main(str(path))[0]
    torch.testing.assert_close(image, torch.tensor([0.0, 0.0, 1.0]).expand(1, 2, 2, 3))


def test_missing_file_forces_refresh(tmp_path):
    path = str(tmp_path / "missing.png")
    assert CidLoadImageFromPath.IS_CHANGED(path) != CidLoadImageFromPath.IS_CHANGED(path)
