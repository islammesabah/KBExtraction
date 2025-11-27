from kbdebugger.types import ExtractionResult, TripletSOP
from typing import Any
import re
import json

# -------------------------
# Robust JSON post-processing helpers
# -------------------------
def _strip_markdown_fences(text: str) -> str:
    # remove ```json ... ``` or ``` ... ```
    return re.sub(r"```(?:json)?\s*|```", "", text, flags=re.IGNORECASE).strip()

def _extract_json_object(text: str) -> str | None:
    """
    Try to locate a top-level JSON object {...} even if the model added extra text.
    Uses a simple brace counter to find the first balanced object.
    """
    s = _strip_markdown_fences(text)
    start = s.find("{")
    if start == -1:
        # no opening brace found
        return None
    depth = 0
    for i, ch in enumerate(s[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start:i+1]
    return None

def _ensure_json_object(raw: str) -> str:
    """
    Best-effort: ensure we return a valid JSON object string.
    - First: try json.loads(raw) directly.
    - Second: try to extract a {...} from noisy output.
    - Otherwise: return "{}".
    """
    s = raw.strip()
    if not s:
        return "{}"

    # 1) Try direct parse
    try:
        data = json.loads(s)
        # Must be an object, not array/string/etc.
        if isinstance(data, dict):
            return s
    except json.JSONDecodeError:
        pass

    # 2) Try extracting just the object portion
    obj_str = _extract_json_object(s)
    if obj_str is None:
        return "{}"

    try:
        data = json.loads(obj_str)
        if isinstance(data, dict):
            return obj_str
    except json.JSONDecodeError:
        return "{}"

    return "{}"
