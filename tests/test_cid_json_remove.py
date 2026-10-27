"""Tests for CidJsonRemove nested path deletion."""

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


def _load_cid_json_remove():
    root = Path(__file__).resolve().parents[1]
    package_name = "cid_node_pack_test_remove"

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
        f"{package_name}.nodes.cid_json_remove",
        root / "nodes" / "cid_json_remove.py",
    )
    node_module = importlib.util.module_from_spec(node_spec)
    sys.modules[node_spec.name] = node_module
    node_spec.loader.exec_module(node_module)
    return node_module.CidJsonRemove


CidJsonRemove = _load_cid_json_remove()


@pytest.fixture
def node():
    return CidJsonRemove()


def test_top_level_remove_still_works(node):
    result = node.main('{"name": "cid", "keep": true}', "name")

    assert json.loads(result[0]) == {"keep": True}


def test_nested_object_path_removes_target_only(node):
    payload = {
        "key_a": {
            "key_b": {
                "key_c": "remove",
                "keep": "stay",
            }
        }
    }

    result = node.main(json.dumps(payload), "key_a/key_b/key_c")

    assert json.loads(result[0]) == {"key_a": {"key_b": {"keep": "stay"}}}


def test_existing_list_index_removes_item(node):
    payload = {"items": [{"name": "first"}, {"name": "second"}]}

    result = node.main(json.dumps(payload), "items/0")

    assert json.loads(result[0]) == {"items": [{"name": "second"}]}


def test_negative_index_removes_from_end(node):
    payload = {"items": [{"name": "first"}, {"name": "second"}]}

    result = node.main(json.dumps(payload), "items/-1")

    assert json.loads(result[0]) == {"items": [{"name": "first"}]}


def test_numeric_segment_inside_dict_is_key(node):
    payload = {"items": {"0": "zero", "1": "one"}}

    result = node.main(json.dumps(payload), "items/0")

    assert json.loads(result[0]) == {"items": {"1": "one"}}


def test_missing_nested_key_is_no_op(node):
    payload = {"key_a": {"key_b": {"keep": "stay"}}}

    result = node.main(json.dumps(payload), "key_a/key_b/missing")

    assert json.loads(result[0]) == payload


def test_top_level_slash_key_wins_over_path(node):
    payload = {
        "key_a/key_b": "literal",
        "key_a": {"key_b": "nested"},
    }

    result = node.main(json.dumps(payload), "key_a/key_b")

    assert json.loads(result[0]) == {"key_a": {"key_b": "nested"}}
