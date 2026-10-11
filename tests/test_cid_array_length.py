"""Tests for CidArrayLength array length lookup."""

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


def _load_cid_array_length():
    root = Path(__file__).resolve().parents[1]
    package_name = "cid_node_pack_test"

    package = types.ModuleType(package_name)
    package.__path__ = [str(root)]
    nodes_package = types.ModuleType(f"{package_name}.nodes")
    nodes_package.__path__ = [str(root / "nodes")]
    utils_package = types.ModuleType(f"{package_name}.utils")
    utils_package.__path__ = [str(root / "utils")]

    sys.modules[package_name] = package
    sys.modules[f"{package_name}.nodes"] = nodes_package
    sys.modules[f"{package_name}.utils"] = utils_package

    json_utils_spec = importlib.util.spec_from_file_location(
        f"{package_name}.utils.json_utils",
        root / "utils" / "json_utils.py",
    )
    json_utils_module = importlib.util.module_from_spec(json_utils_spec)
    sys.modules[json_utils_spec.name] = json_utils_module
    json_utils_spec.loader.exec_module(json_utils_module)

    node_spec = importlib.util.spec_from_file_location(
        f"{package_name}.nodes.cid_array_length",
        root / "nodes" / "cid_array_length.py",
    )
    node_module = importlib.util.module_from_spec(node_spec)
    sys.modules[node_spec.name] = node_module
    node_spec.loader.exec_module(node_module)
    return node_module.CidArrayLength


CidArrayLength = _load_cid_array_length()


@pytest.fixture
def node():
    return CidArrayLength()


def test_returns_length_of_array(node):
    result = node.main('[{"name": "a"}, {"name": "b"}, {"name": "c"}]')

    assert result == (3,)


def test_empty_array_returns_zero(node):
    result = node.main("[]")

    assert result == (0,)


def test_strips_markdown_code_fence(node):
    result = node.main('```json\n[1, 2]\n```')

    assert result == (2,)


def test_empty_input_raises(node):
    with pytest.raises(ValueError, match="empty"):
        node.main("")


def test_invalid_json_raises(node):
    with pytest.raises(ValueError, match="json_str"):
        node.main("[1, 2,")


def test_non_array_raises(node):
    payload = {"items": [1, 2]}

    with pytest.raises(TypeError, match="not an array"):
        node.main(json.dumps(payload))
