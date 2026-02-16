from __future__ import annotations

"""
JSON-sanitization helpers for Flask responses.

We keep UI/API responses strictly JSON-serializable.
"""

from datetime import date, datetime
from typing import Any


def to_jsonable(obj: Any) -> Any:
    """
    Convert `obj` into a JSON-serializable structure.

    Supported conversions
    ---------------------
    - datetime/date -> ISO 8601 string
    - dict -> dict with values sanitized recursively
    - list/tuple/set -> list with items sanitized recursively
    - primitives -> returned as-is
    - fallback -> string

    Parameters
    ----------
    obj:
        Arbitrary Python object.

    Returns
    -------
    Any
        JSON-serializable representation.
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(x) for x in obj]

    return str(obj)
