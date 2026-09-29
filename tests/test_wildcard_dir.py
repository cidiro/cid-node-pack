"""Tests for the configurable wildcards directory in CidWildcardProcessor."""

import pytest

from nodes import cid_wildcard_processor as mod
from nodes.cid_wildcard_processor import CidWildcardProcessor


@pytest.fixture
def proc():
    return CidWildcardProcessor()


@pytest.fixture
def wildcards(tmp_path, monkeypatch):
    (tmp_path / "color.txt").write_text("red\n")
    (tmp_path / "animal.yaml").write_text("pets:\n  - cat\n")
    (tmp_path / "shapes").mkdir()
    (tmp_path / "shapes" / "round.txt").write_text("circle\n")
    monkeypatch.setenv(mod.WILDCARDS_ENV, str(tmp_path))
    return tmp_path


def test_env_var_selects_directory(wildcards):
    assert mod.get_wildcards_dir() == wildcards


@pytest.mark.parametrize("value", [None, "", "   "])
def test_default_when_unset_or_empty(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(mod.WILDCARDS_ENV, raising=False)
    else:
        monkeypatch.setenv(mod.WILDCARDS_ENV, value)
    assert mod.get_wildcards_dir() == mod.DEFAULT_WILDCARDS_DIR


@pytest.mark.parametrize("ref, expected", [
    ("color", "red"),
    ("animal", "cat"),
    ("shapes", "circle"),
])
def test_references_resolve_from_configured_dir(proc, wildcards, ref, expected):
    assert proc._expand(f"__{ref}__") == expected


def test_missing_reference(proc, wildcards):
    assert proc._expand("__nope__") == "[Missing reference: nope]"
