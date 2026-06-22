"""Tests for the reusable variable system in CidWildcardProcessor."""

import pytest

from nodes.cid_wildcard_processor import CidWildcardProcessor


@pytest.fixture
def proc():
    return CidWildcardProcessor()


# -----------------------------------------------------------------------
# _extract_variable_declarations
# -----------------------------------------------------------------------
class TestExtractVariableDeclarations:
    def test_single_line_variable(self):
        text = "$color = {red|blue}\nhello $color"
        decls, remaining = CidWildcardProcessor._extract_variable_declarations(text)
        assert decls == [("color", "{red|blue}")]
        assert remaining == "hello $color"

    def test_multi_line_variable(self):
        text = (
            "$loc = {\n"
            "bedroom\n"
            "|kitchen\n"
            "}\n"
            "at $loc"
        )
        decls, remaining = CidWildcardProcessor._extract_variable_declarations(text)
        assert len(decls) == 1
        assert decls[0][0] == "loc"
        assert "{" in decls[0][1]
        assert "bedroom" in decls[0][1]
        assert "kitchen" in decls[0][1]
        assert remaining.strip() == "at $loc"

    def test_nested_braces(self):
        text = (
            "$x = {a|{b|c}}\n"
            "use $x"
        )
        decls, remaining = CidWildcardProcessor._extract_variable_declarations(text)
        assert len(decls) == 1
        assert decls[0][0] == "x"
        assert decls[0][1] == "{a|{b|c}}"
        assert remaining == "use $x"

    def test_multiple_variables(self):
        text = (
            "$a = foo\n"
            "$b = bar\n"
            "prompt $a $b"
        )
        decls, remaining = CidWildcardProcessor._extract_variable_declarations(text)
        assert len(decls) == 2
        assert decls[0] == ("a", "foo")
        assert decls[1] == ("b", "bar")
        assert remaining == "prompt $a $b"

    def test_unclosed_braces_raises(self):
        text = "$x = {a|b\nno closing"
        with pytest.raises(ValueError, match="Unclosed braces"):
            CidWildcardProcessor._extract_variable_declarations(text)

    def test_no_variables(self):
        text = "just a regular prompt"
        decls, remaining = CidWildcardProcessor._extract_variable_declarations(text)
        assert decls == []
        assert remaining == text

    def test_hyphen_in_var_name(self):
        text = "$my-var = hello\nuse $my-var"
        decls, remaining = CidWildcardProcessor._extract_variable_declarations(text)
        assert decls == [("my-var", "hello")]
        assert remaining == "use $my-var"

    def test_complex_multiline_nested(self):
        text = (
            "$location = {\n"
            "bedroom,{ plush toys,|}\n"
            "|\n"
            "{option_a::4\n"
            "|option_b::1\n"
            "|::2}\n"
            "::3\n"
            "|\n"
            "::0\n"
            "}\n"
            "at $location"
        )
        decls, remaining = CidWildcardProcessor._extract_variable_declarations(text)
        assert len(decls) == 1
        assert decls[0][0] == "location"
        # The value should contain all the nested content
        val = decls[0][1]
        assert "bedroom" in val
        assert "plush toys" in val
        assert "option_a" in val
        assert remaining.strip() == "at $location"


# -----------------------------------------------------------------------
# _resolve_variables
# -----------------------------------------------------------------------
class TestResolveVariables:
    def test_simple_resolution(self, proc):
        decls = [("color", "{red|blue}")]
        import random
        random.seed(42)
        resolved = proc._resolve_variables(decls)
        assert "color" in resolved
        assert resolved["color"] in ("red", "blue")

    def test_inter_variable_reference(self, proc):
        decls = [
            ("color", "red"),
            ("desc", "a $color cat"),
        ]
        resolved = proc._resolve_variables(decls)
        assert resolved["color"] == "red"
        assert resolved["desc"] == "a red cat"

    def test_reverse_order_dependency(self, proc):
        """Variables declared out of dependency order should still resolve."""
        decls = [
            ("desc", "a $color cat"),
            ("color", "red"),
        ]
        resolved = proc._resolve_variables(decls)
        assert resolved["color"] == "red"
        assert resolved["desc"] == "a red cat"

    def test_circular_reference_raises(self, proc):
        decls = [
            ("a", "$b"),
            ("b", "$a"),
        ]
        with pytest.raises(ValueError, match="Circular variable reference"):
            proc._resolve_variables(decls)

    def test_duplicate_declaration_raises(self, proc):
        decls = [
            ("x", "one"),
            ("x", "two"),
        ]
        with pytest.raises(ValueError, match="Duplicate variable declaration"):
            proc._resolve_variables(decls)

    def test_chain_of_three(self, proc):
        decls = [
            ("c", "result: $b"),
            ("a", "hello"),
            ("b", "$a world"),
        ]
        resolved = proc._resolve_variables(decls)
        assert resolved["a"] == "hello"
        assert resolved["b"] == "hello world"
        assert resolved["c"] == "result: hello world"


# -----------------------------------------------------------------------
# _substitute_variables
# -----------------------------------------------------------------------
class TestSubstituteVariables:
    def test_basic_substitution(self):
        result = CidWildcardProcessor._substitute_variables(
            "a $color cat", {"color": "red"}
        )
        assert result == "a red cat"

    def test_multiple_occurrences(self):
        result = CidWildcardProcessor._substitute_variables(
            "$x and $x again", {"x": "foo"}
        )
        assert result == "foo and foo again"

    def test_undefined_variable_raises(self):
        with pytest.raises(ValueError, match="Undefined variable"):
            CidWildcardProcessor._substitute_variables(
                "hello $unknown", {}
            )

    def test_multiple_variables(self):
        result = CidWildcardProcessor._substitute_variables(
            "$a meets $b", {"a": "cat", "b": "dog"}
        )
        assert result == "cat meets dog"


# -----------------------------------------------------------------------
# main() integration
# -----------------------------------------------------------------------
class TestMainWithVariables:
    def test_single_variable_reuse(self, proc):
        text = "$color = {red}\na $color cat with $color eyes"
        result = proc.main(text, seed=0)
        assert result == ("a red cat with red eyes",)

    def test_no_variables_still_works(self, proc):
        text = "{red|blue} sky"
        result = proc.main(text, seed=42)
        assert result[0] in ("red sky", "blue sky")

    def test_escaped_dollar(self, proc):
        text = "costs \\$5"
        result = proc.main(text, seed=0)
        assert result == ("costs $5",)

    def test_escaped_dollar_not_treated_as_variable(self, proc):
        text = "$x = hello\n\\$x is not a variable, but $x is"
        result = proc.main(text, seed=0)
        assert result == ("$x is not a variable, but hello is",)

    def test_variable_with_wildcard(self, proc):
        text = "$animal = {cat|dog}\nmy $animal"
        result = proc.main(text, seed=42)
        animal = result[0].replace("my ", "")
        assert animal in ("cat", "dog")

    def test_variable_referencing_variable(self, proc):
        text = (
            "$color = red\n"
            "$desc = a $color cat\n"
            "$desc is here"
        )
        result = proc.main(text, seed=0)
        assert result == ("a red cat is here",)

    def test_multiline_variable(self, proc):
        text = (
            "$x = {\n"
            "alpha\n"
            "|beta\n"
            "}\n"
            "chose $x"
        )
        result = proc.main(text, seed=42)
        assert result[0] in ("chose alpha", "chose beta")

    def test_circular_reference_in_main(self, proc):
        text = "$a = $b\n$b = $a\nhello"
        with pytest.raises(ValueError, match="Circular"):
            proc.main(text, seed=0)

    def test_undefined_variable_in_prompt(self, proc):
        text = "hello $undefined"
        with pytest.raises(ValueError, match="Undefined variable"):
            proc.main(text, seed=0)

    def test_unclosed_braces_in_main(self, proc):
        text = "$x = {a|b\nuse $x"
        with pytest.raises(ValueError, match="Unclosed braces"):
            proc.main(text, seed=0)

    def test_deterministic_with_seed(self, proc):
        text = "$color = {red|green|blue}\na $color cat with $color eyes"
        r1 = proc.main(text, seed=123)
        r2 = proc.main(text, seed=123)
        assert r1 == r2

    def test_variable_value_consistent_across_uses(self, proc):
        text = "$color = {red|green|blue}\n$color $color $color"
        result = proc.main(text, seed=99)
        parts = result[0].split()
        assert len(parts) == 3
        assert parts[0] == parts[1] == parts[2]
