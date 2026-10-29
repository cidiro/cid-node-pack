"""Backend image-manifest contract; ComfyUI supplies torch and folder_paths."""
import importlib.util
from pathlib import Path
import sys
import types

import pytest

torch = pytest.importorskip('torch')


@pytest.fixture
def backend(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, 'folder_paths', types.SimpleNamespace(get_temp_directory=lambda: str(tmp_path)))
    path = Path(__file__).resolve().parents[1] / 'nodes' / 'cid_image_ab_testing.py'
    spec = importlib.util.spec_from_file_location('cid_ab_backend', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_nested_mixed_batches_and_fresh_sessions(backend, tmp_path):
    inputs = [[torch.zeros(2, 3, 4, 3), torch.ones(1, 5, 6, 4)]]
    first = backend.CidImageABTesting().main(inputs, [30])
    second = backend.CidImageABTesting().main(inputs, [30])
    a, b = first['ui']['cid_ab'][0], second['ui']['cid_ab'][0]
    assert a['id'] != b['id']
    assert a['budget'] == 30
    assert len(a['images']) == 3
    assert a['images'][0]['id'] != a['images'][1]['id']
    assert a['images'][0]['fingerprint'] == a['images'][1]['fingerprint']
    assert a['images'][2]['source'] == [0, 1, 0]
    for image in a['images']:
        p = image['preview']
        assert (tmp_path / p['subfolder'] / p['filename']).is_file()
    assert first['result'] == ()
    assert backend.CidImageABTesting.RETURN_TYPES == ()


@pytest.mark.parametrize('value', [[], [torch.zeros(1, 3, 4)], [torch.zeros(1, 0, 2, 3)], [torch.full((1, 2, 2, 3), float('nan'))], [None]])
def test_invalid_images(backend, value):
    with pytest.raises(ValueError):
        backend.CidImageABTesting().main(value, [30])
