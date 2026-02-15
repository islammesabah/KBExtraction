from typing import Any, Dict, Mapping
import re
import json
import rich
from pathlib import Path
from datetime import datetime, timezone, date, time
import dataclasses
from uuid import UUID

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
    if not isinstance(raw, str):
        return {}

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

def to_jsonable(obj: Any) -> Any:
    """
    Convert `obj` into a JSON-serializable structure.

    Supported conversions
    ---------------------
    - primitives -> as-is
    - datetime/date and objects with .isoformat() -> ISO 8601 string
    - Path, UUID -> string
    - dataclasses -> dict
    - pydantic models -> dict
    - dict/list/tuple/set -> recursively converted
    - otherwise -> TypeError (fail fast)

    Notes
    -----
    We intentionally DO NOT use a blanket `str(obj)` fallback for all unknown
    objects because it can silently hide bugs and create confusing payloads.
    """
    # Primitives
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    # Datetime/date
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    # Common non-JSON primitives
    if isinstance(obj, (Path, UUID)):
        return str(obj)

    # Neo4j temporal types and similar objects
    iso = getattr(obj, "isoformat", None)
    if callable(iso):
        return iso()

    # Dataclasses
    if dataclasses.is_dataclass(obj):
        return {k: to_jsonable(v) for k, v in dataclasses.asdict(obj).items()}  # type: ignore[arg-type]

    # Pydantic v2 / v1
    model_dump = getattr(obj, "model_dump", None)
    if callable(model_dump):
        return to_jsonable(model_dump())
    model_dict = getattr(obj, "dict", None)
    if callable(model_dict):
        return to_jsonable(model_dict())

    # Containers
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(x) for x in obj]

    # Fail fast: unknown type
    raise TypeError(
        f"Object of type {type(obj).__name__} is not JSON-serializable: {obj!r}"
    )



# def _json_default(obj: Any) -> Any:
#     """
#     Fallback encoder for objects that the stdlib json module can't serialize.

#     Handles:
#       - datetime/date/time -> ISO 8601 strings
#       - pathlib.Path -> string
#       - dataclasses -> dict
#       - objects with .isoformat() (e.g., neo4j.time.DateTime) -> ISO string
#       - objects with .dict() / model_dump() (pydantic) -> dict
#       - otherwise -> string repr as a last resort
#     """
#     if isinstance(obj, (datetime, date, time)):
#         return obj.isoformat()

#     if isinstance(obj, Path):
#         return str(obj)

#     if dataclasses.is_dataclass(obj):
#         return dataclasses.asdict(obj) # type: ignore

#     # Neo4j temporal types (neo4j.time.DateTime, Date, etc.) typically support isoformat()
#     iso = getattr(obj, "isoformat", None)
#     if callable(iso):
#         return iso()

#     # Pydantic v1 / v2
#     if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
#         return obj.model_dump()
#     if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
#         return obj.dict()

#     # Last resort: stringify
#     return str(obj)

def write_json(
    path: str | Path, 
    data: Mapping[str, Any], 
    *, 
    indent: int = 2
    ) -> None:
    """
    Write JSON data to disk, creating parent directories if needed.

    Parameters
    ----------
    path:
        Destination file path. Parent directories will be created automatically.

    data:
        JSON-serializable mapping (dict-like). Use `Mapping[str, Any]` to keep
        the helper broadly usable.

    indent:
        JSON pretty-print indentation. Default: 2 (human-readable logs).
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    # created_at = now_utc_compact()

    with p.open("w", encoding="utf-8") as f:
        json.dump(
            dict(data),
            f,
            ensure_ascii=False,
            indent=indent,
            # default=_json_default,
            default=to_jsonable,
        )


