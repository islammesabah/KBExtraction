from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Sequence

from kbdebugger.utils.time import now_utc_human

from .types import KeptQuality, DroppedQuality, SubgraphSimilarityFilterConfig


def build_qualities_to_subgraph_similarity_payload(
    *,
    cfg: SubgraphSimilarityFilterConfig,
    kept: Sequence[KeptQuality],
    dropped: Sequence[DroppedQuality],
) -> Dict:
    """
    Build the Stage 3 log payload.

    Philosophy: minimal + consistent with other stages.
    - No reshaping of outputs
    - No sampling
    - Just stable metadata for UI
    """
    created_at = now_utc_human()

    return {
        "config": asdict(cfg),
        "num_input_qualities": int(len(kept) + len(dropped)),
        "num_kept": len(kept),
        "num_dropped": len(dropped),
        "kept_qualities": kept,
        "dropped_qualities": dropped,
        "created_at": created_at,
    }
