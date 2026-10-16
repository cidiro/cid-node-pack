"""Tests for CidStringToInt string-to-integer conversion."""

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


CidStringToInt = _load_node_class(
    Path(__file__).resolve().parents[1] / "nodes" / "cid_string_to_int.py",
    "CidStringToInt",
)


@pytest.fixture
def node():
    return CidStringToInt()


@pytest.mark.parametrize(
    "value,rounding,expected",
    [
        ("0", "round", 0),
        ("42", "round", 42),
        ("-7", "round", -7),
        ("  10  ", "round", 10),
        ("2e3", "round", 2000),
        ("", "round", 0),
        ("3.5", "round", 4),
        ("3.5", "floor", 3),
        ("3.5", "ceil", 4),
        ("3.5", "truncate", 3),
        ("-3.5", "round", -4),
        ("-3.5", "floor", -4),
        ("-3.5", "ceil", -3),
        ("-3.5", "truncate", -3),
    ],
)
def test_parses_strings(node, value, rounding, expected):
    assert node.main(value, rounding) == (expected,)


def test_result_is_int(node):
    result = node.main("2.0", "round")[0]
    assert isinstance(result, int)


@pytest.mark.parametrize("value", ["abc", "1.2.3", "12abc"])
def test_raises_on_invalid_strings(node, value):
    with pytest.raises(ValueError, match="String to Int"):
        node.main(value, "round")


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_raises_on_non_finite_values(node, value):
    with pytest.raises(ValueError, match="not a finite number"):
        node.main(value, "round")


def test_input_types_and_metadata(node):
    inputs = node.INPUT_TYPES()
    assert list(inputs["required"].keys()) == ["string", "rounding"]
    assert inputs["required"]["rounding"][0] == ["round", "floor", "ceil", "truncate"]
    assert node.RETURN_TYPES == ("INT",)
    assert node.RETURN_NAMES == ("int",)
