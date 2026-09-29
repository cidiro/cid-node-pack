import logging
import os
import random
import re
from collections import deque
from pathlib import Path
from typing import Dict, List, Tuple
import yaml  # PyYAML – for YAML wildcard support

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logger = logging.getLogger("cid_node_pack")
logger.setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent.parent  # <repo>/custom_nodes/cid-node-pack
DEFAULT_WILDCARDS_DIR: Path = BASE_DIR / "wildcards"
WILDCARDS_ENV = "CID_WILDCARDS_DIR"  # overrides DEFAULT_WILDCARDS_DIR when set

REFERENCE_PATTERN = re.compile(r"__([^_]+)__")    # e.g. __settings__, __path/to/thing__
WILDCARD_PATTERN = re.compile(r"\{([^{}]+)\}")  # e.g. {foo|bar|baz}
WEIGHT_DELIMITER = "::"                             # e.g. red::3
TXT_EXT = ".txt"
YAML_EXTS = (".yml", ".yaml")  # Supported YAML file extensions
MAX_ITERATIONS = 100

# Variable system constants
VAR_DECL_RE = re.compile(r"^\$([a-zA-Z_][a-zA-Z0-9_-]*)\s*=\s*(.*)$", re.MULTILINE)
VAR_REF_RE = re.compile(r"\$([a-zA-Z_][a-zA-Z0-9_-]*)")
ESCAPED_DOLLAR_PLACEHOLDER = "\x00DOLLAR\x00"

_warned_missing_dirs: set = set()


def get_wildcards_dir() -> Path:
    """Return the wildcards directory: $CID_WILDCARDS_DIR if set, else <pack>/wildcards."""
    configured = os.environ.get(WILDCARDS_ENV, "").strip()
    wildcards_dir = Path(configured).expanduser() if configured else DEFAULT_WILDCARDS_DIR
    if configured and not wildcards_dir.is_dir() and wildcards_dir not in _warned_missing_dirs:
        _warned_missing_dirs.add(wildcards_dir)
        logger.warning("%s points to a missing directory: %s", WILDCARDS_ENV, wildcards_dir)
    return wildcards_dir


class CidWildcardProcessor:
    """ComfyUI node that expands wildcard references and inline option groups.

    Supported syntax
    ----------------
    1. **Inline option groups** – `{red|green|blue}`
       * Add weights with `::` – `{red::3|blue}` → red has weight 3.
    2. **File / directory references** – `__reference__` or `__path/to/reference__`
       * The wildcards directory is `$CID_WILDCARDS_DIR` if set, else `<pack>/wildcards`.
       * Looks for `<wildcards>/<reference>.txt` first.
       * If not found, treats it as directory `<wildcards>/<reference>/` and recursively collects
         all `.txt` files inside.
       * Each non-empty line becomes a candidate; weights via `::` are supported.

    Processing is recursive – newly-introduced patterns are expanded until no changes are
    detected or *MAX_ITERATIONS* is reached.
    """

    # ---------------------------------------------------------------------
    # ComfyUI metadata
    # ---------------------------------------------------------------------
    @classmethod
    def INPUT_TYPES(cls) -> dict:  # noqa: N802 – ComfyUI API
        return {
            "required": {
                "text": ("STRING", {"multiline": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
            }
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Text"

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    @staticmethod
    def _strip_comment_from_line(line: str) -> str:
        """Remove a trailing comment (starting at '#') from a single line.

        A hash ('#') is treated as a comment delimiter only if it is not escaped.
        An escaped hash ('\\#') is preserved as a literal '#', with the escape
        backslash removed in the output.
        """
        result_chars: List[str] = []
        backslashes_in_run = 0

        for ch in line:
            if ch == "\\":
                result_chars.append(ch)
                backslashes_in_run += 1
                continue

            if ch == "#":
                if backslashes_in_run % 2 == 1:
                    # The '#' is escaped; drop one preceding backslash and keep '#'
                    if result_chars:
                        result_chars.pop()
                    result_chars.append("#")
                    backslashes_in_run = 0
                    continue
                # Unescaped '#': start of comment → stop processing the line
                break

            # Regular character resets the backslash run
            result_chars.append(ch)
            backslashes_in_run = 0

        return "".join(result_chars).rstrip()

    @staticmethod
    def _strip_comments(text: str) -> str:
        """Remove comments from each line in a multi-line string (escape-aware)."""
        lines = text.splitlines()
        processed = [CidWildcardProcessor._strip_comment_from_line(line) for line in lines]
        return "\n".join(processed)

    @staticmethod
    def _expand_weighted(token: str) -> List[str]:
        """Expand a single *token* into a list respecting optional weight.

        Examples
        --------
        >>> _expand_weighted('red') -> ['red']
        >>> _expand_weighted('blue::3') -> ['blue', 'blue', 'blue']
        """
        if WEIGHT_DELIMITER in token:
            value, weight_str = token.rsplit(WEIGHT_DELIMITER, 1)
            try:
                weight = int(weight_str)
            except ValueError:
                logger.warning("Invalid weight '%s' in token '%s' – treating as 1", weight_str, token)
                return [value]
            return [value] * max(weight, 0)
        return [token]

    @staticmethod
    def _gather_lines_from_file(file_path: Path) -> List[str]:
        """Return all non-empty lines from *file_path*, stripping whitespace."""
        try:
            with file_path.open("r", encoding="utf-8") as f:
                processed: List[str] = []
                for raw_line in f:
                    content = CidWildcardProcessor._strip_comment_from_line(raw_line).strip()
                    if content:
                        processed.append(content)
                return processed
        except Exception as exc:  # pragma: no cover – broad except for node robustness
            logger.info("Error reading file %s: %s", file_path, exc)
            return []

    # ------------------------------------------------------------------
    # YAML helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _flatten_yaml(data) -> List[str]:
        """Recursively collect all leaf values from a YAML structure."""
        if isinstance(data, dict):
            values: List[str] = []
            for v in data.values():
                values.extend(CidWildcardProcessor._flatten_yaml(v))
            return values
        elif isinstance(data, list):
            values: List[str] = []
            for item in data:
                values.extend(CidWildcardProcessor._flatten_yaml(item))
            return values
        else:
            # Convert non-string leaf nodes to string, ignore None
            return [str(data)] if data is not None else []

    @staticmethod
    def _gather_values_from_yaml(file_path: Path) -> List[str]:
        """Return all leaf string values from a YAML file."""
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            values = CidWildcardProcessor._flatten_yaml(data)
            processed: List[str] = []
            for value in values:
                content = CidWildcardProcessor._strip_comment_from_line(str(value)).strip()
                if content:
                    processed.append(content)
            return processed
        except Exception as exc:  # pragma: no cover – broad except for node robustness
            logger.info("Error reading YAML file %s: %s", file_path, exc)
            return []

    @classmethod
    def _gather_lines_from_directory(cls, dir_path: Path) -> List[str]:
        """Recursively collect non-empty lines from all `.txt`, `.yml`, and `.yaml` files inside *dir_path*."""
        lines: List[str] = []
        # Collect from .txt files
        for text_file in dir_path.rglob(f"*{TXT_EXT}"):
            lines.extend(cls._gather_lines_from_file(text_file))
        # Collect from YAML files
        for ext in YAML_EXTS:
            for yaml_file in dir_path.rglob(f"*{ext}"):
                lines.extend(cls._gather_values_from_yaml(yaml_file))
        return lines

    # ------------------------------------------------------------------
    # Regex callbacks
    # ------------------------------------------------------------------
    def _process_reference(self, match: re.Match) -> str:  # noqa: D401 – imperative mood ok
        """Replace wildcard *reference* with a randomly-selected line from file(s)."""
        reference: str = match.group(1)

        wildcards_dir = get_wildcards_dir()
        txt_candidate = wildcards_dir / f"{reference}{TXT_EXT}"
        yaml_candidates = [wildcards_dir / f"{reference}{ext}" for ext in YAML_EXTS]
        dir_candidate = wildcards_dir / reference

        # 1) Single file – <reference>.txt
        if txt_candidate.is_file():
            lines = self._gather_lines_from_file(txt_candidate)
            if not lines:
                return f"[Empty file: {reference}{TXT_EXT}]"
        # 2) Single YAML file – <reference>.yml / .yaml
        else:
            yaml_file = next((c for c in yaml_candidates if c.is_file()), None)
            if yaml_file is not None:
                lines = self._gather_values_from_yaml(yaml_file)
                if not lines:
                    return f"[Empty file: {reference}{yaml_file.suffix}]"
            # 3) Directory containing many wildcard files
            elif dir_candidate.is_dir():
                lines = self._gather_lines_from_directory(dir_candidate)
                if not lines:
                    return f"[No wildcard content in directory: {reference}]"
            # 4) Nothing found ➜ return placeholder message
            else:
                return f"[Missing reference: {reference}]"

        # Apply weights & choose one value
        weighted: List[str] = []
        for line in lines:
            weighted.extend(self._expand_weighted(line))
        return random.choice(weighted) if weighted else f"[No valid options for: {reference}]"

    def _process_wildcard(self, match: re.Match) -> str:  # noqa: D401 – imperative mood ok
        """Randomly choose an option from a *{foo|bar}* group, respecting weights."""
        tokens = match.group(1).split("|")
        weighted: List[str] = []
        for token in tokens:
            weighted.extend(self._expand_weighted(token))
        return random.choice(weighted) if weighted else ""  # safeguard – should not be empty

    # ------------------------------------------------------------------
    # Variable system
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_variable_declarations(
        text: str,
    ) -> Tuple[List[Tuple[str, str]], str]:
        """Parse ``$var = value`` declarations from *text*.

        Returns
        -------
        (declarations, remaining_text)
            *declarations* is a list of ``(name, raw_value)`` tuples in source
            order.  Multi-line values are supported when braces are unbalanced
            – accumulation continues until brace depth returns to zero.
        """
        lines = text.split("\n")
        declarations: List[Tuple[str, str]] = []
        remaining_lines: List[str] = []

        i = 0
        while i < len(lines):
            match = re.match(
                r"^\$([a-zA-Z_][a-zA-Z0-9_-]*)\s*=\s*(.*)", lines[i]
            )
            if match:
                var_name = match.group(1)
                first_part = match.group(2)
                value_parts = [first_part]
                depth = first_part.count("{") - first_part.count("}")

                while depth > 0:
                    i += 1
                    if i >= len(lines):
                        raise ValueError(
                            f"Unclosed braces in variable declaration "
                            f"'${var_name}': reached end of text with "
                            f"brace depth {depth}"
                        )
                    value_parts.append(lines[i])
                    depth += lines[i].count("{") - lines[i].count("}")

                declarations.append((var_name, "\n".join(value_parts)))
            else:
                remaining_lines.append(lines[i])
            i += 1

        return declarations, "\n".join(remaining_lines)

    def _expand(self, text: str) -> str:
        """Run iterative reference + wildcard expansion on *text*."""
        current = text
        previous = None
        iterations = 0

        while current != previous and iterations < MAX_ITERATIONS:
            iterations += 1
            previous = current
            current = self._strip_comments(current)
            current = REFERENCE_PATTERN.sub(self._process_reference, current)
            current = WILDCARD_PATTERN.sub(self._process_wildcard, current)

        if iterations == MAX_ITERATIONS:
            logger.warning(
                "Reached max iterations (%d) while expanding wildcards.",
                MAX_ITERATIONS,
            )
        return current

    @staticmethod
    def _substitute_variables(
        text: str, resolved: Dict[str, str],
    ) -> str:
        """Replace all ``$varname`` references in *text* with resolved values.

        Raises :class:`ValueError` if an undefined variable is referenced.
        """
        def _replace(match: re.Match) -> str:
            name = match.group(1)
            if name in resolved:
                return resolved[name]
            raise ValueError(f"Undefined variable '${name}'")

        return VAR_REF_RE.sub(_replace, text)

    def _resolve_variables(
        self,
        declarations: List[Tuple[str, str]],
    ) -> Dict[str, str]:
        """Resolve variable declarations in dependency order.

        Uses topological sort to handle inter-variable references.
        Raises :class:`ValueError` on circular or undefined references.
        """
        # Build lookup: name → raw value
        raw: Dict[str, str] = {}
        for name, value in declarations:
            if name in raw:
                raise ValueError(
                    f"Duplicate variable declaration: '${name}'"
                )
            raw[name] = value

        declared_names = set(raw.keys())

        # Build dependency graph
        deps: Dict[str, set] = {name: set() for name in declared_names}
        for name, value in raw.items():
            for ref_match in VAR_REF_RE.finditer(value):
                ref = ref_match.group(1)
                if ref in declared_names:
                    deps[name].add(ref)

        # Topological sort – Kahn's algorithm
        in_degree: Dict[str, int] = {name: 0 for name in declared_names}
        reverse: Dict[str, List[str]] = {
            name: [] for name in declared_names
        }
        for name, dep_set in deps.items():
            in_degree[name] = len(dep_set)
            for dep in dep_set:
                reverse[dep].append(name)

        queue = deque(
            name for name, deg in in_degree.items() if deg == 0
        )
        order: List[str] = []

        while queue:
            name = queue.popleft()
            order.append(name)
            for dependent in reverse[name]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(order) != len(declared_names):
            remaining = declared_names - set(order)
            raise ValueError(
                "Circular variable reference involving: "
                + ", ".join(f"${n}" for n in sorted(remaining))
            )

        # Resolve in topological order
        resolved: Dict[str, str] = {}
        for name in order:
            value = raw[name]
            # Substitute already-resolved variable references
            if VAR_REF_RE.search(value):
                value = self._substitute_variables(value, resolved)
            # Expand wildcards and file references
            value = self._expand(value)
            # Final comment strip and whitespace cleanup
            value = self._strip_comments(value).strip()
            resolved[name] = value

        return resolved

    # ------------------------------------------------------------------
    # Main entrypoint (ComfyUI)
    # ------------------------------------------------------------------
    def main(self, text: str, seed: int) -> Tuple[str]:  # noqa: D401
        """Expand *text* deterministically given *seed*.

        Returns
        -------
        (expanded_text,)
        """
        random.seed(seed)

        # 0) Protect escaped dollar signs
        current = text.replace("\\$", ESCAPED_DOLLAR_PLACEHOLDER)

        # 1) Strip comments
        current = self._strip_comments(current)

        # 2) Extract variable declarations (brace-balanced, multi-line)
        declarations, current = self._extract_variable_declarations(current)

        # 3) Resolve all variables in dependency order
        resolved = self._resolve_variables(declarations) if declarations else {}

        # 4) Substitute resolved variables into the remaining prompt text
        if resolved:
            current = self._substitute_variables(current, resolved)

        # 4b) Error on any remaining variable references
        remaining_ref = VAR_REF_RE.search(current)
        if remaining_ref:
            raise ValueError(
                f"Undefined variable '${remaining_ref.group(1)}'"
            )

        # 5) Expand wildcards and file references in the prompt
        current = self._expand(current)

        # 6) Final comment strip
        current = self._strip_comments(current)

        # 7) Restore escaped dollar signs
        current = current.replace(ESCAPED_DOLLAR_PLACEHOLDER, "$")

        return (current,)
