from typing import List, TypedDict, Literal
from kbdebugger.types import TripletSubjectObjectPredicate, GraphRelation

# In our codebase, Qualities is typically something like: list[str]
# We keep it explicit here for clarity and strictness.
Quality = str


class NeighborHit(TypedDict):
    """
    One nearest-neighbor hit from the KG vector index.

    - relation:
        The KG relation (GraphRelation) whose sentence was similar to the query vector.

    - score:
        Cosine similarity in [0, 1]. Higher means more similar.
    """
    relation: GraphRelation
    score: float


class KeptQuality(TypedDict):
    """
    A quality sentence that passed the similarity threshold.

    - quality:
        The original atomic sentence/quality text.

    - max_score:
        The highest similarity score among the nearest neighbors.
        The score is between the quality (candidate sentence) and its most similar KG relation sentence.

    - neighbors:
        The top-k most similar KG relations. These are kept as context for the
        next stage (e.g., triplet extraction or LLM comparator).
    """
    quality: Quality
    max_score: float
    neighbors: List[NeighborHit]


class DroppedQuality(TypedDict):
    """
    A quality sentence that failed the similarity threshold.

    - quality:
        The original atomic sentence/quality text.

    - max_score:
        The best similarity score observed. Useful for debugging/tuning threshold.
    """
    quality: Quality
    max_score: float
