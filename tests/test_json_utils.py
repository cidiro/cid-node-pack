"""Tests for the tolerant JSON parsing helpers in utils/json_utils.py."""

import importlib.util
import json
from pathlib import Path

import pytest


def _load_json_utils():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "cid_json_utils_test", root / "utils" / "json_utils.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


json_utils = _load_json_utils()

# The input that produced the original crash: plain LLM prose containing
# brackets, wired into a JSON node's json_str input.
INCIDENT_PROSE = (
    "[Shot 1]) is fully referenced.\n"
    "\n"
    "integrated_multimodal_description: [Shot 1]"
)


@pytest.fixture
def extract():
    return json_utils.extract_json_from_string


@pytest.fixture
def parse():
    return json_utils.parse_json_data


# --- extract_json_from_string -------------------------------------------


def test_extract_returns_valid_json_unchanged(extract):
    assert extract('{"a": 1}') == '{"a": 1}'
    assert extract("  [1, 2]  ") == "[1, 2]"


def test_extract_strips_markdown_fences(extract):
    assert extract('```json\n{"a": 1}\n```') == '{"a": 1}'


def test_extract_finds_json_surrounded_by_prose(extract):
    text = 'Sure! Here it is:\n{"a": 1}\nHope that helps!'
    assert extract(text) == '{"a": 1}'


def test_extract_finds_array_in_prose(extract):
    assert extract("The list [1, 2, 3] is what you want.") == "[1, 2, 3]"


def test_extract_skips_prose_brackets_and_finds_later_json(extract):
    text = 'As stated in [note 4), see {"a": 1} for details.'
    assert extract(text) == '{"a": 1}'


def test_extract_does_not_mangle_prose_with_brackets(extract):
    # Regression test: prose brackets must not be sliced into a fake JSON
    # fragment; the input is returned unchanged so errors show the truth.
    assert extract(INCIDENT_PROSE) == INCIDENT_PROSE


# --- repair_json_string --------------------------------------------------


def test_repair_escapes_raw_newlines_and_tabs_in_strings():
    broken = '{"a": "line1\nline2\tend"}'
    repaired = json_utils.repair_json_string(broken)
    assert repaired == '{"a": "line1\\nline2\\tend"}'
    assert json.loads(repaired) == {"a": "line1\nline2\tend"}


def test_repair_converts_single_quoted_strings():
    repaired = json_utils.repair_json_string("{'a': 'he said \"hi\"'}")
    assert json.loads(repaired) == {"a": 'he said "hi"'}


def test_repair_converts_smart_quotes():
    assert json.loads(json_utils.repair_json_string('{"a": “b”}')) == {"a": "b"}


def test_repair_removes_trailing_commas():
    assert json.loads(json_utils.repair_json_string('{"a": 1,}')) == {"a": 1}
    assert json.loads(json_utils.repair_json_string("[1, 2,]")) == [1, 2]


def test_repair_closes_missing_brackets():
    assert json.loads(json_utils.repair_json_string('{"a": [1, 2')) == {"a": [1, 2]}


def test_repair_fixes_mismatched_and_stray_closing_brackets():
    assert json.loads(json_utils.repair_json_string('{"a": 1]')) == {"a": 1}
    assert json.loads(json_utils.repair_json_string("[1, 2]]")) == [1, 2]


def test_repair_maps_python_literals():
    broken = '{"a": True, "b": False, "c": None}'
    assert json.loads(json_utils.repair_json_string(broken)) == {
        "a": True,
        "b": False,
        "c": None,
    }


def test_repair_fixes_invalid_escape_sequences():
    # The raw text contains  {"a": "C:\d"}  with an invalid \d escape.
    broken = '{"a": "C:\\d"}'
    assert json.loads(json_utils.repair_json_string(broken)) == {"a": "C:\\d"}


def test_repair_keeps_valid_unicode_escapes():
    assert json.loads(json_utils.repair_json_string('{"u": "\\u00e9"}')) == {"u": "é"}


def test_repair_removes_comments():
    broken = "{\n  // a note\n  \"a\": 1 /* inline */, /* x */ \"b\": 2\n}"
    assert json.loads(json_utils.repair_json_string(broken)) == {"a": 1, "b": 2}


def test_repair_leaves_brackets_inside_strings_alone():
    # Brackets and escaped characters inside string values are protected
    # content and must not be counted as structure or altered.
    valid = '{"desc": "uses [Shot 1] and \\n escapes"}'
    assert json_utils.repair_json_string(valid) == valid
    assert json.loads(valid) == {"desc": "uses [Shot 1] and \n escapes"}


# --- parse_json_data ------------------------------------------------------


def test_parse_recovers_multiline_string_values(parse):
    broken = '{"desc": "Shot 1) is fully referenced.\nSee [Shot 1]."}'
    assert parse(broken) == {"desc": "Shot 1) is fully referenced.\nSee [Shot 1]."}


def test_parse_recovers_broken_json_without_prose(parse):
    broken = "{'a': 'b',\n 'c': True,}"
    assert parse(broken) == {"a": "b", "c": True}


def test_parse_repairs_outer_object_before_accepting_inner_array(parse):
    # The inner ["a"] is valid JSON on its own, but the broken outer object
    # must win: it is repaired and parsed as a whole.
    broken = '{"items": ["a"], "desc": "line1\nline2"}'
    assert parse(broken) == {"items": ["a"], "desc": "line1\nline2"}


def test_parse_yaml_fallback_for_key_value_text(parse):
    assert parse("key: value\nother: [a, b]") == {
        "key": "value",
        "other": ["a", "b"],
    }


def test_parse_yaml_fallback_for_flow_collections(parse):
    broken = "{integrated_multimodal_description: [Shot 1]}"
    assert parse(broken) == {"integrated_multimodal_description": ["Shot 1"]}


def test_empty_input_defaults_to_empty_object(parse):
    assert parse("") == {}


def test_whitespace_input_raises(parse):
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse("   ")


def test_parse_plain_prose_raises_value_error(parse):
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse(INCIDENT_PROSE)
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse("no structure at all, just words")
