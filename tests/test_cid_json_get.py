"""Tests for CidJsonGet nested path lookup."""

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


def _load_cid_json_get():
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
        f"{package_name}.nodes.cid_json_get",
        root / "nodes" / "cid_json_get.py",
    )
    node_module = importlib.util.module_from_spec(node_spec)
    sys.modules[node_spec.name] = node_module
    node_spec.loader.exec_module(node_module)
    return node_module.CidJsonGet


CidJsonGet = _load_cid_json_get()


@pytest.fixture
def node():
    return CidJsonGet()


def test_gets_top_level_value(node):
    result = node.main('{"name": "cid"}', "name")

    assert result == ("cid",)


def test_gets_nested_object_value(node):
    payload = {"key_a": {"key_b": {"key_c": "found"}}}

    result = node.main(json.dumps(payload), "key_a/key_b/key_c")

    assert result == ("found",)


def test_gets_nested_array_value(node):
    payload = {"items": [{"name": "first"}, {"name": "second"}]}

    result = node.main(json.dumps(payload), "items/1/name")

    assert result == ("second",)


def test_numeric_segment_inside_dict_is_key(node):
    payload = {"items": {"0": {"name": "zero"}}}

    result = node.main(json.dumps(payload), "items/0/name")

    assert result == ("zero",)


def test_returns_nested_container_as_json(node):
    payload = {"items": [{"name": "first"}]}

    result = node.main(json.dumps(payload), "items/0")

    assert json.loads(result[0]) == {"name": "first"}


def test_missing_nested_key_raises_with_context(node):
    payload = {"key_a": {"key_b": {"key_c": "found"}}}

    with pytest.raises(KeyError, match="key_a/key_b/missing"):
        node.main(json.dumps(payload), "key_a/key_b/missing")


def test_negative_index_counts_from_end(node):
    payload = {"items": ["a", "b", "c", "d", "e", "f", "g"]}

    result = node.main(json.dumps(payload), "items/-5")

    assert result == ("c",)


def test_negative_last_index(node):
    payload = {"items": ["a", "b"]}

    result = node.main(json.dumps(payload), "items/-1")

    assert result == ("b",)


def test_negative_index_inside_nested_path(node):
    payload = {"items": [{"name": "first"}, {"name": "second"}]}

    result = node.main(json.dumps(payload), "items/-1/name")

    assert result == ("second",)


def test_negative_zero_behaves_like_zero(node):
    payload = {"items": ["a", "b"]}

    result = node.main(json.dumps(payload), "items/-0")

    assert result == ("a",)


def test_negative_index_out_of_range_raises(node):
    payload = {"items": ["a", "b"]}

    with pytest.raises(IndexError, match="list index -3 out of range"):
        node.main(json.dumps(payload), "items/-3")


def test_positive_index_out_of_range_raises(node):
    payload = {"items": ["a", "b"]}

    with pytest.raises(IndexError, match="list index 2 out of range"):
        node.main(json.dumps(payload), "items/2")


def test_invalid_list_index_raises(node):
    payload = {"items": [{"name": "first"}]}

    with pytest.raises(TypeError, match="expected a list index"):
        node.main(json.dumps(payload), "items/one/name")


def test_lone_minus_is_not_an_index(node):
    payload = {"items": ["a"]}

    with pytest.raises(TypeError, match="expected a list index"):
        node.main(json.dumps(payload), "items/-")


def test_top_level_slash_key_wins_over_path(node):
    payload = {
        "key_a/key_b": "literal",
        "key_a": {"key_b": "nested"},
    }

    result = node.main(json.dumps(payload), "key_a/key_b")

    assert result == ("literal",)
