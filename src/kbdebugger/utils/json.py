from kbdebugger.types import ExtractionResult, TripletSOP
from typing import Any, Dict
import re
import json

import rich

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
    text = _strip_markdown_fences(text)
    start = text.find("{")
    if start == -1:
        # no opening brace found
        return None
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    return None

def _extract_json_array(text: str) -> str | None:
    """
    Extract the first balanced JSON array '[ ... ]' substring.
    """
    text = _strip_markdown_fences(text)
    start = text.find("[")
    if start == -1:
        return None

    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None

def ensure_json_object(raw: str) -> Dict[str, Any]:
    """
    Best-effort: ensure we return a *parsed* JSON object (dict).
    - First: try json.loads(raw) directly.
    - Second: try to extract a {...} from noisy output.
    - Otherwise: return {}.
    """
    s = raw.strip()
    if not s:
        return {}

    # 1. Try direct parse
    try:
        data = json.loads(s)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # 2. Maybe noisy output with {...}? Try extracting just the object portion
    obj_str = _extract_json_object(s)
    if obj_str is None:
        return {}

    try:
        data = json.loads(obj_str)
        if isinstance(data, dict):
            rich.print("[ensure_json_object] ✅ Successfully extracted valid JSON object.")
            return data
    except json.JSONDecodeError as e:
        rich.print(f"[ensure_json_object] ⚠️ Extracted JSON object is invalid: {e}")

    return {}

def ensure_json_array(raw: str) -> Any:
    """
    Best-effort: ensure we return a valid JSON array.
    Accepts noisy LLM output and extracts the FIRST valid JSON array `[ ... ]`.

    Returns:
        - A Python list (loaded JSON array), OR
        - [] as fallback.
    """
    if not raw or not raw.strip():
        return []

    s = raw.strip()

    # 1. Try direct parse
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass

    # 2. Try to extract a clean `[ ... ]` from noise
    arr_str = _extract_json_array(s)
    if arr_str is None:
        # As a fallback, try extracting a single object
        # (rare case where model returned only one item incorrectly)
        obj_str = _extract_json_object(s)
        if obj_str:
            try:
                parsed = json.loads(obj_str)
                return [parsed] if isinstance(parsed, dict) else []
            except Exception:
                return []
        return []

    # 3. Validate array
    try:
        parsed = json.loads(arr_str)
        if isinstance(parsed, list):
            rich.print("[ensure_json_array] ✅ Extracted valid JSON array.")
            return parsed
    except Exception:
        rich.print("[ensure_json_array] ⚠️ Extracted JSON array is invalid.")

    return []