"""Tests for CidJsonAppend nested path appends."""

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


def _load_cid_json_append():
    root = Path(__file__).resolve().parents[1]
    package_name = "cid_node_pack_test_append"

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
        f"{package_name}.nodes.cid_json_append",
        root / "nodes" / "cid_json_append.py",
    )
    node_module = importlib.util.module_from_spec(node_spec)
    sys.modules[node_spec.name] = node_module
    node_spec.loader.exec_module(node_module)
    return node_module.CidJsonAppend


CidJsonAppend = _load_cid_json_append()


@pytest.fixture
def node():
    return CidJsonAppend()


def test_top_level_existing_list_appends(node):
    result = node.main("items", '"second"', '{"items": ["first"]}')

    assert json.loads(result[0]) == {"items": ["first", "second"]}


def test_missing_top_level_key_creates_list(node):
    result = node.main("items", '"first"', "{}")

    assert json.loads(result[0]) == {"items": ["first"]}


def test_nested_existing_list_appends(node):
    payload = {"key_a": {"key_b": ["first"]}}

    result = node.main("key_a/key_b", '"second"', json.dumps(payload))

    assert json.loads(result[0]) == {"key_a": {"key_b": ["first", "second"]}}


def test_missing_nested_list_creates_dict_parents(node):
    result = node.main("key_a/key_b/key_c", "123", "{}")

    assert json.loads(result[0]) == {"key_a": {"key_b": {"key_c": [123]}}}


def test_existing_list_path_appends_to_nested_list(node):
    payload = {"items": [{"tags": ["old"]}]}

    result = node.main("items/0/tags", '"new"', json.dumps(payload))

    assert json.loads(result[0]) == {"items": [{"tags": ["old", "new"]}]}


def test_negative_index_path_appends_to_nested_list(node):
    payload = {"items": [{"tags": ["old"]}, {"tags": ["other"]}]}

    result = node.main("items/-1/tags", '"new"', json.dumps(payload))

    assert json.loads(result[0]) == {
        "items": [{"tags": ["old"]}, {"tags": ["other", "new"]}]
    }


def test_top_level_slash_key_wins_over_path(node):
    payload = {
        "key_a/key_b": ["literal"],
        "key_a": {"key_b": ["nested"]},
    }

    result = node.main("key_a/key_b", '"updated"', json.dumps(payload))

    assert json.loads(result[0]) == {
        "key_a/key_b": ["literal", "updated"],
        "key_a": {"key_b": ["nested"]},
    }


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("123", 123),
        ('{"name": "cid"}', {"name": "cid"}),
        ('["a", "b"]', ["a", "b"]),
        ("true", True),
        ("plain", "plain"),
        ("('python', 'tuple')", ["python", "tuple"]),
    ],
)
def test_value_parsing_matches_json_add(node, value, expected):
    result = node.main("items", value, "{}")

    assert json.loads(result[0]) == {"items": [expected]}


def test_existing_non_list_target_raises(node):
    with pytest.raises(TypeError, match="not a list"):
        node.main("items", '"new"', '{"items": "old"}')


def test_nested_non_list_target_raises(node):
    payload = {"key_a": {"key_b": {"key_c": "old"}}}

    with pytest.raises(TypeError, match="not a list"):
        node.main("key_a/key_b/key_c", '"new"', json.dumps(payload))


def test_missing_list_parent_raises(node):
    with pytest.raises(TypeError, match="requires an existing list"):
        node.main("items/0/tags", '"new"', "{}")
