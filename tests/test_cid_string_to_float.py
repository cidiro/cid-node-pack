"""Tests for CidStringToFloat string-to-float conversion."""

import importlib.util
import sys
import types
from pathlib import Path

import pytest


def _load_node_class(module_file, class_name):
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

    node_spec = importlib.util.spec_from_file_location(
        f"{package_name}.nodes.{module_file.stem}",
        module_file,
    )
    node_module = importlib.util.module_from_spec(node_spec)
    sys.modules[node_spec.name] = node_module
    node_spec.loader.exec_module(node_module)
    return getattr(node_module, class_name)


CidStringToFloat = _load_node_class(
    Path(__file__).resolve().parents[1] / "nodes" / "cid_string_to_float.py",
    "CidStringToFloat",
)


@pytest.fixture
def node():
    return CidStringToFloat()


@pytest.mark.parametrize(
    "value,expected",
    [
        ("0", 0.0),
        ("1", 1.0),
        ("-1", -1.0),
        ("3.5", 3.5),
        ("  2.75  ", 2.75),
        ("1e3", 1000.0),
        ("-0.5", -0.5),
        ("", 0.0),
    ],
)
def test_parses_valid_strings(node, value, expected):
    assert node.main(value) == (expected,)


def test_result_is_float(node):
    result = node.main("2")[0]
    assert isinstance(result, float)


@pytest.mark.parametrize("value", ["abc", "1.2.3", "nan-ignored", "12abc"])
def test_raises_on_invalid_strings(node, value):
    with pytest.raises(ValueError, match="String to Float"):
        node.main(value)


def test_input_types_and_metadata(node):
    inputs = node.INPUT_TYPES()
    (name,) = inputs["required"].keys()
    assert name == "string"
    assert node.RETURN_TYPES == ("FLOAT",)
    assert node.RETURN_NAMES == ("float",)
