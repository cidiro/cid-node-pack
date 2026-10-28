"""Tests for CidAnyToString any-to-string conversion."""

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


def _load_cid_any_to_string():
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

    any_type_spec = importlib.util.spec_from_file_location(
        f"{package_name}.utils.any_type",
        root / "utils" / "any_type.py",
    )
    any_type_module = importlib.util.module_from_spec(any_type_spec)
    sys.modules[any_type_spec.name] = any_type_module
    any_type_spec.loader.exec_module(any_type_module)

    node_spec = importlib.util.spec_from_file_location(
        f"{package_name}.nodes.cid_any_to_string",
        root / "nodes" / "cid_any_to_string.py",
    )
    node_module = importlib.util.module_from_spec(node_spec)
    sys.modules[node_spec.name] = node_module
    node_spec.loader.exec_module(node_module)
    return node_module.CidAnyToString


CidAnyToString = _load_cid_any_to_string()


@pytest.fixture
def node():
    return CidAnyToString()


@pytest.mark.parametrize(
    "value,expected",
    [
        ("hello", "hello"),
        ("", ""),
        (42, "42"),
        (-1, "-1"),
        (3.5, "3.5"),
        (True, "True"),
        (False, "False"),
        (None, "None"),
    ],
)
def test_casts_primitives(node, value, expected):
    assert node.main(value) == (expected,)


def test_casts_containers_as_json(node):
    assert node.main({"a": 1, "b": [2, 3]}) == (json.dumps({"a": 1, "b": [2, 3]}, indent=2),)
    assert node.main([1, "two", None]) == (json.dumps([1, "two", None], indent=2),)
    assert node.main((1, 2)) == (json.dumps((1, 2), indent=2),)


def test_json_fallback_to_str(node):
    class Unserializable:
        def __repr__(self):
            return "<unserializable>"

    # default=str keeps most objects serializable, so verify the repr path
    # through a container that still cannot be dumped.
    value = {1j: "complex key"}
    assert node.main(value) == (str(value),)


def test_describes_tensor_like_values(node):
    class FakeTensor:
        shape = [1, 2, 3]
        dtype = "float32"

    result = node.main(FakeTensor())[0]
    assert result == "FakeTensor(shape=(1, 2, 3), dtype=float32)"


def test_casts_arbitrary_objects_with_str(node):
    class Custom:
        def __str__(self):
            return "custom-value"

    assert node.main(Custom()) == ("custom-value",)
