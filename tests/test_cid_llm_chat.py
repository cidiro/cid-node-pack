"""Tests for CidLLMChat payload building and structured-output (json_schema) handling."""

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


def _load_cid_llm_chat():
    root = Path(__file__).resolve().parents[1]
    package_name = "cid_node_pack_test_llm_chat"

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
        f"{package_name}.nodes.cid_llm_chat",
        root / "nodes" / "cid_llm_chat.py",
    )
    node_module = importlib.util.module_from_spec(node_spec)
    sys.modules[node_spec.name] = node_module
    node_spec.loader.exec_module(node_module)
    return node_module.CidLLMChat


@pytest.fixture
def llm_chat_class():
    return _load_cid_llm_chat()


@pytest.fixture
def llm_chat(llm_chat_class):
    return llm_chat_class()


SIMPLE_SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}}}


class TestInputTypes:
    def test_user_prompt_is_a_required_input_slot(self, llm_chat_class):
        inputs = llm_chat_class.INPUT_TYPES()
        config = inputs["required"]["user_prompt"][1]
        assert inputs["required"]["user_prompt"][0] == "STRING"
        assert config["forceInput"] is True

    def test_json_schema_is_an_optional_input_slot(self, llm_chat_class):
        inputs = llm_chat_class.INPUT_TYPES()
        assert "json_schema" not in inputs["required"]
        config = inputs["optional"]["json_schema"][1]
        assert inputs["optional"]["json_schema"][0] == "STRING"
        assert config["forceInput"] is True


class TestParseJsonSchema:
    def test_empty_input_returns_none(self, llm_chat):
        assert llm_chat._parse_json_schema("") is None
        assert llm_chat._parse_json_schema("   ") is None
        assert llm_chat._parse_json_schema(None) is None

    def test_parses_plain_schema_object(self, llm_chat):
        raw = json.dumps(SIMPLE_SCHEMA)
        assert llm_chat._parse_json_schema(raw) == SIMPLE_SCHEMA

    def test_parses_schema_with_markdown_fences(self, llm_chat):
        raw = "```json\n" + json.dumps(SIMPLE_SCHEMA) + "\n```"
        assert llm_chat._parse_json_schema(raw) == SIMPLE_SCHEMA

    def test_invalid_json_raises_value_error(self, llm_chat):
        with pytest.raises(ValueError, match="json_schema"):
            llm_chat._parse_json_schema("not a schema")

    def test_non_object_schema_raises_value_error(self, llm_chat):
        with pytest.raises(ValueError, match="JSON Schema object"):
            llm_chat._parse_json_schema("[1, 2]")


class TestBuildPayload:
    def _build(self, llm_chat, parsed_schema=None, max_completion_tokens=-1):
        return llm_chat._build_payload(
            model_name="test-model",
            request_messages=[{"role": "user", "content": "Hi"}],
            parsed_schema=parsed_schema,
            temperature=0.6,
            top_p=0.95,
            top_k=20,
            min_p=0.0,
            presence_penalty=0.0,
            repeat_penalty=1.0,
            repeat_last_n=64,
            dry_multiplier=0.0,
            max_completion_tokens=max_completion_tokens,
        )

    def test_no_schema_omits_response_format(self, llm_chat):
        payload = self._build(llm_chat, parsed_schema=None)
        assert "response_format" not in payload
        assert payload["model"] == "test-model"
        assert payload["messages"] == [{"role": "user", "content": "Hi"}]
        assert payload["stream"] is False
        assert "max_completion_tokens" not in payload

    def test_schema_adds_openai_style_response_format(self, llm_chat):
        payload = self._build(llm_chat, parsed_schema=SIMPLE_SCHEMA)
        assert payload["response_format"] == {
            "type": "json_schema",
            "json_schema": {
                "name": "response",
                "strict": True,
                "schema": SIMPLE_SCHEMA,
            },
        }

    def test_positive_max_completion_tokens_is_included(self, llm_chat):
        payload = self._build(llm_chat, parsed_schema=None, max_completion_tokens=128)
        assert payload["max_completion_tokens"] == 128


class TestValidateStructuredResponse:
    def test_valid_json_passes(self, llm_chat):
        llm_chat._validate_structured_response('{"answer": "42"}', SIMPLE_SCHEMA)

    def test_valid_json_with_fences_passes(self, llm_chat):
        llm_chat._validate_structured_response('```json\n{"answer": "42"}\n```', SIMPLE_SCHEMA)

    def test_non_json_response_raises_runtime_error(self, llm_chat):
        with pytest.raises(RuntimeError, match="not valid JSON"):
            llm_chat._validate_structured_response("I cannot answer that.", SIMPLE_SCHEMA)

    def test_type_mismatch_raises_runtime_error(self, llm_chat):
        with pytest.raises(RuntimeError, match="does not match"):
            llm_chat._validate_structured_response("[1, 2]", SIMPLE_SCHEMA)

    def test_schema_without_declared_type_skips_type_check(self, llm_chat):
        schema = {"properties": {"answer": {"type": "string"}}}
        llm_chat._validate_structured_response("[1, 2]", schema)

    def test_union_type_matches_any_member(self, llm_chat):
        schema = {"type": ["object", "null"]}
        llm_chat._validate_structured_response("null", schema)


class TestMainIntegration:
    def _make_node(self, llm_chat, response_content):
        node = llm_chat
        node._health_check = lambda base_url_value: None
        node._ensure_model_loaded = lambda base_url_value, model_name: None
        captured = {}

        def fake_request_json(method, url, payload=None):
            captured["method"] = method
            captured["url"] = url
            captured["payload"] = payload
            return {
                "choices": [{"message": {"role": "assistant", "content": response_content}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
            }

        node._request_json = fake_request_json
        return node, captured

    def test_main_sends_schema_as_response_format(self, llm_chat):
        node, captured = self._make_node(llm_chat, '{"answer": "42"}')
        response, raw_response, updated_messages = node.main(
            user_prompt="What is the answer?",
            model="test-model",
            base_url="http://127.0.0.1:8080",
            json_schema=json.dumps(SIMPLE_SCHEMA),
        )

        assert captured["method"] == "POST"
        assert captured["url"].endswith("/v1/chat/completions")
        assert captured["payload"]["response_format"]["json_schema"]["schema"] == SIMPLE_SCHEMA
        assert response == '{"answer": "42"}'
        assert json.loads(updated_messages)[-1]["content"] == '{"answer": "42"}'
        assert json.loads(raw_response)["choices"][0]["message"]["content"] == '{"answer": "42"}'

    def test_main_without_schema_omits_response_format(self, llm_chat):
        node, captured = self._make_node(llm_chat, "Plain text answer.")
        response, _, _ = node.main(
            user_prompt="What is the answer?",
            model="test-model",
            base_url="http://127.0.0.1:8080",
        )

        assert "response_format" not in captured["payload"]
        assert response == "Plain text answer."

    def test_main_raises_when_schema_constrained_response_is_not_json(self, llm_chat):
        node, _ = self._make_node(llm_chat, "I cannot answer that.")
        with pytest.raises(RuntimeError, match="not valid JSON"):
            node.main(
                user_prompt="What is the answer?",
                model="test-model",
                base_url="http://127.0.0.1:8080",
                json_schema=json.dumps(SIMPLE_SCHEMA),
            )

    def test_main_raises_on_invalid_schema_input(self, llm_chat):
        node, _ = self._make_node(llm_chat, '{"answer": "42"}')
        with pytest.raises(ValueError, match="json_schema"):
            node.main(
                user_prompt="What is the answer?",
                model="test-model",
                base_url="http://127.0.0.1:8080",
                json_schema="not a schema",
            )
