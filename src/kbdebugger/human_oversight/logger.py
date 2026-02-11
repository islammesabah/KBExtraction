from __future__ import annotations

from typing import Mapping, Sequence

from kbdebugger.utils.json import write_json
from kbdebugger.utils.time import now_utc_compact
from kbdebugger.types import GraphRelation


def save_human_oversight_log(
    *,
    accepted: Sequence[GraphRelation],
    rejected: Sequence[GraphRelation],
) -> str:
    """
    Log human oversight decisions to JSON.

    JSON structure:
    {
      "created_at": "...",
      "number_accepted": ...,
      "number_rejected": ...,
      "accepted": [...],
      "rejected": [...]
    }
    """
    created_at = now_utc_compact()
    path = f"logs/06_human_oversight_{created_at}.json"

    data: Mapping[str, object] = {
        "created_at": created_at,
        "number_accepted": len(accepted),
        "number_rejected": len(rejected),
        "accepted": list(accepted),
        "rejected": list(rejected),
    }

    write_json(path, data)
    print(f"\n[INFO] 🧾🧑‍⚖️ Human oversight log written to {path}")
    return path
