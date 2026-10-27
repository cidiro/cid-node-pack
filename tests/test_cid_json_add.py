"""Tests for CidJsonAdd nested path updates."""

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


def _load_cid_json_add():
    root = Path(__file__).resolve().parents[1]
    package_name = "cid_node_pack_test_add"

    package = types.ModuleType(package_name)
    package.__path__ = [str(root)]
    nodes_package = types.ModuleType(f"{package_name}.nodes")
    nodes_package.__path__ = [str(root / "nodes")]
    utils_package = types.ModuleType(f"{package_name}.utils")
    utils_package.__path__ = [str(root / "utils")]

    sys.modules[package_name] = package
    sys.modules[f"{package_name}.nodes"] = nodes_package
    sys.modules[f"{package_name}.utils"] = utils_package

    node_spec = importlib.util.spec_from_file_location(
        f"{package_name}.nodes.cid_json_add",
        root / "nodes" / "cid_json_add.py",
    )
    node_module = importlib.util.module_from_spec(node_spec)
    sys.modules[node_spec.name] = node_module
    node_spec.loader.exec_module(node_module)
    return node_module.CidJsonAdd


CidJsonAdd = _load_cid_json_add()


@pytest.fixture
def node():
    return CidJsonAdd()


def test_top_level_update_still_works(node):
    result = node.main("name", '"updated"', '{"name": "old"}')

    assert json.loads(result[0]) == {"name": "updated"}


def test_nested_object_path_creates_missing_dict_parents(node):
    result = node.main("key_a/key_b/key_c", "123", "{}")

    assert json.loads(result[0]) == {"key_a": {"key_b": {"key_c": 123}}}


def test_existing_list_path_updates_value(node):
    payload = {"items": [{"name": "old"}]}

    result = node.main("items/0/name", '"updated"', json.dumps(payload))

    assert json.loads(result[0]) == {"items": [{"name": "updated"}]}


def test_numeric_segment_inside_dict_is_key(node):
    payload = {"items": {"0": {"name": "old"}}}

    result = node.main("items/0/name", '"updated"', json.dumps(payload))

    assert json.loads(result[0]) == {"items": {"0": {"name": "updated"}}}


def test_top_level_slash_key_wins_over_path(node):
    payload = {
        "key_a/key_b": "literal",
        "key_a": {"key_b": "nested"},
    }

    result = node.main("key_a/key_b", '"updated"', json.dumps(payload))

    assert json.loads(result[0]) == {
        "key_a/key_b": "updated",
        "key_a": {"key_b": "nested"},
    }


def test_negative_index_updates_from_end(node):
    payload = {"items": [{"name": "first"}, {"name": "second"}]}

    result = node.main("items/-1/name", '"updated"', json.dumps(payload))

    assert json.loads(result[0]) == {"items": [{"name": "first"}, {"name": "updated"}]}


def test_negative_index_out_of_range_raises(node):
    with pytest.raises(IndexError, match="list index -1 out of range"):
        node.main("items/-1", '"updated"', '{"items": []}')


def test_missing_list_parent_raises(node):
    with pytest.raises(TypeError, match="requires an existing list"):
        node.main("items/0/name", '"updated"', "{}")
