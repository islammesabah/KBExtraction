from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from .logger import save_human_oversight_log
from .reviewer import review_triplets

from kbdebugger.types import ExtractionResult, GraphRelation


@dataclass(frozen=True, slots=True)
class HumanOversightResult:
    accepted: list[GraphRelation]
    rejected: list[GraphRelation]
    log_path: str


def run_human_oversight(
     triplets: Sequence[ExtractionResult]
) -> HumanOversightResult:
    """
    Public API: review relations, upsert accepted ones, log accepted/rejected.
    """
    accepted, rejected = review_triplets(triplets)
    log_path = save_human_oversight_log(accepted=accepted, rejected=rejected)
    return HumanOversightResult(
        accepted=accepted,
        rejected=rejected,
        log_path=log_path,
    )

