from typing import List, TypedDict, Literal
from kbdebugger.types import TripletSubjectObjectPredicate, GraphRelation
from dataclasses import dataclass

# In our codebase, Qualities is typically something like: list[str]
# We keep it explicit here for clarity and strictness.
Quality = str


@dataclass(frozen=True, slots=True)
class SubgraphSimilarityFilterConfig:
    """
    Configuration for the Vector Similarity Filter stage.

    This stage embeds:
      - each candidate quality sentence
      - each KG relation sentence in the retrieved subgraph
    using a SentenceTransformer encoder, then keeps a quality if its maximum
    similarity to any KG relation sentence exceeds `min_similarity_threshold`.

    Attributes
    ----------
    encoder_model_name:
        HuggingFace model id for the SentenceTransformer encoder used to embed
        both quality sentences and KG relation sentences.

    encoder_device:
        Device string passed to the encoder (e.g. "cpu", "cuda", "cuda:0").
        If None, the backend chooses automatically.

    normalize_embeddings:
        Whether to L2-normalize embeddings (recommended for cosine similarity).

    quality_to_kg_top_k:
        Number of nearest KG relation sentences to retrieve per quality
        (for context + logging, and to compute max_score).

    min_similarity_threshold:
        Minimum cosine similarity required to keep a quality.
    """
    encoder_model_name: str
    encoder_device: str | None # None will let sentence-transformers choose
    normalize_embeddings: bool # Normalizing is recommended for cosine similarity

    quality_to_kg_top_k: int
    min_similarity_threshold: float

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
