"""Tests for CidJsonLoad file lookup and refresh detection."""

import importlib.util
import json
import sys
import time
import types
from pathlib import Path

import pytest


def _load_cid_json_load(input_dir, output_dir):
    root = Path(__file__).resolve().parents[1]
    package_name = "cid_node_pack_test_load"

    package = types.ModuleType(package_name)
    package.__path__ = [str(root)]
    nodes_package = types.ModuleType(f"{package_name}.nodes")
    nodes_package.__path__ = [str(root / "nodes")]
    utils_package = types.ModuleType(f"{package_name}.utils")
    utils_package.__path__ = [str(root / "utils")]

    folder_paths = types.ModuleType("folder_paths")
    folder_paths.get_input_directory = lambda: str(input_dir)
    folder_paths.get_output_directory = lambda: str(output_dir)

    sys.modules[package_name] = package
    sys.modules[f"{package_name}.nodes"] = nodes_package
    sys.modules[f"{package_name}.utils"] = utils_package
    sys.modules["folder_paths"] = folder_paths

    node_spec = importlib.util.spec_from_file_location(
        f"{package_name}.nodes.cid_json_load",
        root / "nodes" / "cid_json_load.py",
    )
    node_module = importlib.util.module_from_spec(node_spec)
    sys.modules[node_spec.name] = node_module
    node_spec.loader.exec_module(node_module)
    return node_module.CidJsonLoad


@pytest.fixture
def json_load_class(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    return _load_cid_json_load(input_dir, output_dir)


def test_loads_and_normalizes_json_from_input_directory(json_load_class, tmp_path):
    file_path = tmp_path / "input" / "data.json"
    file_path.write_text('{"name":"cid","values":[1,2]}', encoding="utf-8")

    result = json_load_class().main("data.json")

    assert json.loads(result[0]) == {"name": "cid", "values": [1, 2]}
    assert result[0] == json.dumps({"name": "cid", "values": [1, 2]}, indent=4)


def test_is_changed_updates_when_file_is_rewritten(json_load_class, tmp_path):
    file_path = tmp_path / "input" / "data.json"
    file_path.write_text('{"value": 1}', encoding="utf-8")
    first_signature = json_load_class.IS_CHANGED("data.json")

    time.sleep(0.001)
    file_path.write_text('{"value": 22}', encoding="utf-8")
    second_signature = json_load_class.IS_CHANGED("data.json")

    assert second_signature != first_signature


def test_absolute_path_lookup(json_load_class, tmp_path):
    file_path = tmp_path / "absolute.json"
    file_path.write_text('{"source": "absolute"}', encoding="utf-8")

    result = json_load_class().main(str(file_path))

    assert json.loads(result[0]) == {"source": "absolute"}


def test_output_directory_lookup(json_load_class, tmp_path):
    file_path = tmp_path / "output" / "data.json"
    file_path.write_text('{"source": "output"}', encoding="utf-8")

    result = json_load_class().main("data.json")

    assert json.loads(result[0]) == {"source": "output"}


def test_is_changed_for_missing_file_forces_refresh(json_load_class):
    assert json_load_class.IS_CHANGED("missing.json") != json_load_class.IS_CHANGED("missing.json")
