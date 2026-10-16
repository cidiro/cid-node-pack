import json
import re

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML ships with ComfyUI
    yaml = None

# Escape sequences that are valid inside JSON string literals.
_JSON_STRING_ESCAPES = '"\\/bfnrt'
_HEX_DIGITS = set("0123456789abcdefABCDEF")


def _clean_markdown(json_str):
    """Strips markdown fences and similar LLM wrapper formatting."""
    s = json_str.strip().lstrip("\ufeff")

    # Remove starting markdown block with optional language specifier
    # e.g., ```json\n or ```\n
    s = re.sub(r"^```[a-zA-Z]*\s*\n", "", s)

    # Remove trailing markdown block
    if s.endswith("```"):
        s = s[:-3].strip()

    # Sometimes it might just have "json" followed by a newline at the start
    if s.lower().startswith("json\n"):
        s = s[5:].strip()

    return s


def _first_valid_value(s):
    """
    Returns the first JSON value embedded in s that parses cleanly: s itself
    when it is valid JSON, otherwise the first valid {...} or [...] slice.
    Brackets from plain prose (for example "[Shot 1]") are skipped because
    they do not form valid JSON. Returns None when nothing parses.
    """
    if not s:
        return None

    try:
        json.loads(s)
        return s
    except ValueError:
        pass

    decoder = json.JSONDecoder()
    for match in re.finditer(r"[{\[]", s):
        start = match.start()
        try:
            _, end = decoder.raw_decode(s, start)
        except ValueError:
            continue
        return s[start:end]

    return None


def extract_json_from_string(json_str):
    """
    Cleans up a string that might contain markdown formatting around JSON
    (common with LLM outputs) and returns the core JSON string.

    If the cleaned string is not valid JSON itself, the first embedded JSON
    object or array that parses cleanly is returned. Slices are only accepted
    when they actually parse, so brackets that merely appear in prose (for
    example "[Shot 1]") no longer produce a mangled fragment. When no valid
    JSON is found, the cleaned input is returned unchanged so that error
    messages show what was actually received.
    """
    s = _clean_markdown(json_str)
    embedded = _first_valid_value(s)
    return s if embedded is None else embedded


def _escape_control_char(ch):
    if ch == "\n":
        return "\\n"
    if ch == "\r":
        return "\\r"
    if ch == "\t":
        return "\\t"
    if ch == "\b":
        return "\\b"
    if ch == "\f":
        return "\\f"
    return "\\u%04x" % ord(ch)


def repair_json_string(json_str):
    """
    Best-effort repair of a broken JSON string (typical LLM mistakes) so that
    protected characters inside string values no longer break parsing.

    It fixes, outside and inside string literals respectively:

    - raw control characters (newlines, tabs, ...) inside string values,
      which are escaped automatically;
    - single-quoted and smart-quoted ("curly quote") strings, converted to
      double-quoted JSON strings;
    - invalid backslash escape sequences, whose backslash gets escaped;
    - Python literals (True/False/None, in any case) mapped to JSON booleans
      and null;
    - trailing commas, // and /* */ comments;
    - stray or mismatched closing brackets, and missing closing brackets.

    Brackets and quotes that appear inside string values are treated as
    protected content: they are kept as-is and never counted as structure.
    """
    out = []
    stack = []
    in_string = False
    quote = '"'
    i = 0
    n = len(json_str)

    while i < n:
        ch = json_str[i]

        if in_string:
            if ch == "\\":
                nxt = json_str[i + 1] if i + 1 < n else ""
                if nxt == "u":
                    digits = json_str[i + 2:i + 6]
                    if len(digits) == 4 and all(c in _HEX_DIGITS for c in digits):
                        out.append(json_str[i:i + 6])
                        i += 6
                        continue
                if nxt == "'":
                    # Python-style escaped quote: \' is not valid JSON.
                    out.append("'")
                    i += 2
                    continue
                if nxt in _JSON_STRING_ESCAPES:
                    out.append("\\" + nxt)
                    i += 2
                    continue
                # Not a valid JSON escape sequence: escape the backslash.
                out.append("\\\\")
                i += 1
                continue
            if ch == quote:
                in_string = False
                out.append('"')
                i += 1
                continue
            if quote == '"' and ch in "“”":
                # Treat a closing smart quote as the string delimiter when it
                # is followed by a structural character; otherwise it is
                # regular (and legal) string content.
                rest = json_str[i + 1:].lstrip()
                if not rest or rest[0] in ":,}]":
                    in_string = False
                    out.append('"')
                else:
                    out.append(ch)
                i += 1
                continue
            if ch == '"':
                # Unescaped double quote inside a single-quoted string.
                out.append('\\"')
                i += 1
                continue
            if ch < " ":
                # Raw control characters are not allowed inside JSON strings.
                out.append(_escape_control_char(ch))
                i += 1
                continue
            out.append(ch)
            i += 1
            continue

        if ch in "“”":
            in_string = True
            quote = '"'
            out.append('"')
            i += 1
            continue
        if ch in "\"'":
            in_string = True
            quote = ch
            out.append('"')
            i += 1
            continue
        if ch == "{":
            stack.append("}")
            out.append(ch)
            i += 1
            continue
        if ch == "[":
            stack.append("]")
            out.append(ch)
            i += 1
            continue
        if ch in "}]":
            if stack:
                # Close with the bracket the opened structure expects; this
                # also repairs mismatched closers such as {'a': 1].
                out.append(stack.pop())
            # A closing bracket without a matching opener is dropped.
            i += 1
            continue
        if ch == ",":
            j = i + 1
            while j < n and json_str[j] in " \t\r\n":
                j += 1
            if j < n and json_str[j] in "}]":
                # Trailing comma right before a closing bracket: drop it.
                i += 1
                continue
            out.append(ch)
            i += 1
            continue
        if ch == "/" and json_str.startswith("//", i):
            end = json_str.find("\n", i)
            i = n if end == -1 else end
            continue
        if ch == "/" and json_str.startswith("/*", i):
            end = json_str.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        if ch.isalpha() or ch == "_":
            j = i + 1
            while j < n and (json_str[j].isalnum() or json_str[j] == "_"):
                j += 1
            word = json_str[i:j]
            lowered = word.lower()
            if lowered in ("true", "false", "null", "none"):
                out.append("null" if lowered == "none" else lowered)
            else:
                out.append(word)
            i = j
            continue
        out.append(ch)
        i += 1

    if in_string:
        out.append('"')
    if stack:
        # Drop trailing whitespace and commas left before the closing
        # brackets that get inserted below.
        while out and out[-1] in " \t\r\n":
            out.pop()
        while out and out[-1] == ",":
            out.pop()
            while out and out[-1] in " \t\r\n":
                out.pop()
        while stack:
            out.append(stack.pop())

    return "".join(out)


def parse_json_data(json_str, input_name="json_str"):
    """
    Parses a JSON string with layered recovery so slightly malformed input
    (typical LLM output) does not immediately fail a workflow.

    In order, the input is: cleaned of markdown formatting, parsed strictly
    as JSON, repaired as a whole (escaped control characters, quotes, commas
    and brackets, see repair_json_string), scanned for the first strictly
    valid embedded JSON value, and finally parsed as YAML, which is a JSON
    superset and also covers "key: value" style output. Only YAML results
    that are objects or arrays are accepted.

    Raises a formatted ValueError when none of that works.
    """
    s = _clean_markdown(json_str) if json_str else "{}"

    first_error = None
    try:
        return json.loads(s)
    except ValueError as e:
        first_error = e

    try:
        return json.loads(repair_json_string(s))
    except ValueError:
        pass

    embedded = _first_valid_value(s)
    if embedded is not None:
        return json.loads(embedded)

    if yaml is not None:
        try:
            yaml_data = yaml.safe_load(s)
            if isinstance(yaml_data, (dict, list)):
                return yaml_data
        except yaml.YAMLError:
            pass

    raise ValueError(
        f"In '{input_name}': {format_json_error(s, first_error)}"
    ) from first_error


def format_json_error(json_str, e):
    """
    Formats a JSONDecodeError with a helpful pointer and the full JSON string.
    """
    try:
        # e.lineno and e.colno are 1-indexed
        lines = json_str.splitlines()
        if not lines:
            return f"Invalid JSON: {e}\nEmpty string."

        line_idx = e.lineno - 1
        col_idx = e.colno - 1

        # Fallback if line somehow out of bounds
        if line_idx >= len(lines):
            return f"Invalid JSON: {e}\nFull string:\n{json_str}"

        error_line = lines[line_idx]

        # Build pointer line
        pointer = " " * col_idx + "^"

        # Show a few lines of context around the error, plus the full string at the bottom
        start_idx = max(0, line_idx - 2)
        end_idx = min(len(lines), line_idx + 3)

        context_lines = []
        for i in range(start_idx, end_idx):
            prefix = "-> " if i == line_idx else "   "
            context_lines.append(f"{prefix}{lines[i]}")
            if i == line_idx:
                context_lines.append(f"   {pointer}")

        context_str = "\n".join(context_lines)

        return f"Invalid JSON: {e}\n\nError context:\n{context_str}\n\nFull string being parsed:\n{json_str}"

    except Exception as fallback_e:
        # Fallback just in case parsing the error fails
        return f"Invalid JSON: {e}\nFull string:\n{json_str}"
