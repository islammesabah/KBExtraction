import ast
import json
from typing import Any, Callable, Dict, TypeVar
import rich

from kbdebugger.utils.json import _extract_json_object

T = TypeVar("T")

def parse_response(
    raw: str,
    *,
    coercer: Callable[[Dict[str, Any]], T],
    default: T,
) -> T:
    """
    Fast, ordered parser for LLM outputs.

    Attempts (in order):
      1. literal_eval(full)
      2. json.loads(full)
      3. literal_eval(extracted {...})
      4. json.loads(extracted {...})

    As soon as a dict is obtained, it is passed to `coercer`.
    If coercer returns a non-default value → return it immediately.

    Otherwise → continue to next attempt.
    If all fail → return default.
    """

    s = raw.strip()
    if not s:
        return default

    # -------------------------
    # Helper: try parser + coercer
    # -------------------------
    def try_parse_and_coerce(parse_fn, input_str, label: str):
        try:
            data = parse_fn(input_str)
            if isinstance(data, dict):
                # rich.print(f"[parse_response] ✅ {label} produced dict.")
                result = coercer(data)
                if result != default and result is not None:
                    # rich.print(f"[parse_response] ✅ coercer accepted dict ({label}).")
                    return result
                else:
                    rich.print(f"[parse_response] ⚠️ coercer rejected dict ({label}).")
        except Exception as e:
            # Parsing failed — silently continue
            rich.print(f"[parse_response] … {label} failed: {e}")
        return None

    # --------------------------------
    # 1. literal_eval(raw)
    # --------------------------------
    out = try_parse_and_coerce(
        lambda x: ast.literal_eval(x),
        s,
        "literal_eval(full)"
    )
    if out is not None:
        return out

    # --------------------------------
    # 2. json.loads(raw)
    # --------------------------------
    out = try_parse_and_coerce(
        lambda x: json.loads(x),
        s,
        "json.loads(full)"
    )
    if out is not None:
        return out

    # --------------------------------
    # Extract {...}
    # --------------------------------
    obj_str = _extract_json_object(s)
    if obj_str:
        # 3. literal_eval(extracted)
        out = try_parse_and_coerce(
            lambda x: ast.literal_eval(x),
            obj_str,
            "literal_eval(extracted)"
        )
        if out is not None:
            return out

        # 4. json.loads(extracted)
        out = try_parse_and_coerce(
            lambda x: json.loads(x),
            obj_str,
            "json.loads(extracted)"
        )
        if out is not None:
            return out

    # --------------------------------
    # All failed
    # --------------------------------
    rich.print("[parse_response] ❌ No valid dict produced. Returning default.")
    return default