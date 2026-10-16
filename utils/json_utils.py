import json
import re

def extract_json_from_string(json_str):
    """
    Cleans up a string that might contain markdown formatting around JSON
    (common with LLM outputs) and returns the core JSON string.
    """
    s = json_str.strip()
    
    # Remove starting markdown block with optional language specifier
    # e.g., ```json\n or ```\n
    s = re.sub(r"^```[a-zA-Z]*\s*\n", "", s)
    
    # Remove trailing markdown block
    if s.endswith("```"):
        s = s[:-3].strip()
        
    # Sometimes it might just have "json" followed by a newline at the start
    if s.lower().startswith("json\n"):
        s = s[5:].strip()
        
    # If the string still doesn't start with { or [, but contains them,
    # we can try to extract the JSON block.
    if not s.startswith("{") and not s.startswith("["):
        # Try to find the first { and last }
        start_dict = s.find("{")
        end_dict = s.rfind("}")
        
        start_list = s.find("[")
        end_list = s.rfind("]")
        
        if start_dict != -1 and end_dict != -1 and (start_list == -1 or start_dict < start_list):
            s = s[start_dict:end_dict+1]
        elif start_list != -1 and end_list != -1:
            s = s[start_list:end_list+1]

    return s

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
