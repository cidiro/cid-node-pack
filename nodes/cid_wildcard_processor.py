import random
import re
import os
import logging
from typing import List, Tuple

logger = logging.getLogger('cid_node_pack')
logger.setLevel(logging.WARNING)


class CidWildcardProcessor:
    """
    Processes wildcard patterns in the format {option1|option2|option3} with support for:

    - File references: __filename__ is replaced by a random line from filename.txt in the wildcards folder.
    - Weighted options: {option1::weight1|option2::weight2|option3} to simulate frequency.

    Nested patterns are processed recursively.
    """

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        return {
            "required": {
                "text": ("STRING", {"multiline": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
            }
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/Text"

    def _expand_weighted(self, text: str) -> List[str]:
        """
        Expand a text that may contain a weight specification using the format '::'.
        For example, "blue::3" becomes ["blue", "blue", "blue"].
        Raises ValueError if the weight specification cannot be converted to an integer.
        """
        if "::" in text:
            option, weight_str = text.rsplit("::", 1)
            weight = int(weight_str)
            return [option] * weight
        return [text]

    def _process_wildcard(self, match: re.Match) -> str:
        """
        Process a wildcard pattern {option1|option2|...} by expanding weighted options
        and selecting one at random.
        """
        options_text = match.group(1)
        options = options_text.split("|")
        expanded_options: List[str] = []
        for option in options:
            expanded_options.extend(self._expand_weighted(option))
        return random.choice(expanded_options)

    def _process_file_reference(self, match: re.Match) -> str:
        """
        Process a file reference __filename__ by reading a random line from the corresponding file.
        The file is expected to be located in the 'wildcards' directory.
        """
        filename = match.group(1)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, "wildcards", f"{filename}.txt")

        if not os.path.isfile(file_path):
            logger.info(f"CidWildcardProcessor - File not found: {filename}.txt")
            return f"[File not found: {filename}.txt]"

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            if not lines:
                logger.info(f"CidWildcardProcessor - Empty file: {filename}.txt")
                return f"[Empty file: {filename}.txt]"

            weighted_lines: List[str] = []
            logger.info(f"CidWildcardProcessor - Processing {len(lines)} lines from {filename}.txt")
            for line in lines:
                weighted_lines.extend(self._expand_weighted(line))
            chosen_line = random.choice(weighted_lines)
            logger.info(f"CidWildcardProcessor - Selected line from {filename}.txt: '{chosen_line}'")
            return chosen_line
        except Exception as e:
            logger.info(f"CidWildcardProcessor - Error reading file {filename}.txt: {e}")
            return f"[Error reading file {filename}.txt: {e}]"

    def main(self, text: str, seed: int) -> Tuple[str]:
        """
        Processes the input text by recursively replacing file references and wildcard patterns.
        The process stops once no further changes are detected or after a maximum number of iterations.
        """
        random.seed(seed)
        logger.info(f"CidWildcardProcessor - Starting with text: {text}")

        processed_text = text
        previous_text = ""
        max_iterations = 100
        iterations = 0

        while previous_text != processed_text and iterations < max_iterations:
            iterations += 1
            previous_text = processed_text

            # Process file references first.
            processed_text = re.sub(r"__([^_]+)__", self._process_file_reference, processed_text)
            logger.info(f"CidWildcardProcessor - After file references (iteration {iterations}): {processed_text}")

            # Process inline wildcard patterns.
            processed_text = re.sub(r"\{([^{}]+)\}", self._process_wildcard, processed_text)
            logger.info(f"CidWildcardProcessor - After wildcards (iteration {iterations}): {processed_text}")

        logger.info(f"CidWildcardProcessor - Final result after {iterations} iterations: {processed_text}")
        return (processed_text,)
