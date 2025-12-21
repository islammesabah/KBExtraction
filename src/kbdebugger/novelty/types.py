from enum import Enum
from typing import Any, Mapping, Optional, Sequence, TypedDict
from dataclasses import dataclass


class NoveltyDecision(str, Enum):
    """Allowed novelty decision labels."""
    EXISTING = "EXISTING"
    PARTIALLY_NEW = "PARTIALLY_NEW"
    NEW = "NEW"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class NeighborView:
    """
    Minimal neighbor view used by the comparator prompt.

    Attributes:
        score: similarity score in [0,1]
        sentence: KG edge sentence string
    """
    score: float
    sentence: str


@dataclass(frozen=True, slots=True)
class QualityNoveltyInput:
    """
    Input to the novelty comparator.

    Attributes:
        quality: the extracted sentence
        neighbors: up to 3 neighbor edges (score + sentence)
    """
    quality: str
    neighbors: Sequence[NeighborView]
    max_score: float


class QualityNoveltyResultRaw(TypedDict):
    """
    JSON schema the model must return.
    i.e., Raw JSON keys expected from the model (best-effort).
    """
    decision: str
    rationale: str
    novel_spans: list[str]
    matched_neighbor_sentence: Optional[str]
    confidence: float


@dataclass(frozen=True, slots=True)
class QualityNoveltyResult:
    """
    Parsed comparator output for a single quality sentence, enriched with context.

    We store `quality` so downstream stages (e.g., triplet extraction) can consume
    novelty results directly without relying on positional alignment with other lists.
    """
    quality: str
    max_score: float

    decision: NoveltyDecision
    rationale: str
    novel_spans: Sequence[str]
    matched_neighbor_sentence: Optional[str]
    confidence: float
