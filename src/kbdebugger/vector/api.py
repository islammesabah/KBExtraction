from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from kbdebugger.extraction.types import Qualities
from kbdebugger.types import GraphRelation
from .encoder import SentenceTransformerEncoder
from .similarity_filter import VectorSimilarityFilter
from .types import KeptQuality, DroppedQuality


@dataclass(frozen=True, slots=True)
class VectorSimilarityFilterConfig:
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


def run_vector_similarity_filter(
    *,
    kg_relations: Sequence[GraphRelation],
    qualities: Qualities,
    cfg: VectorSimilarityFilterConfig,
    pretty_print: bool = True,
) -> Tuple[list[KeptQuality], list[DroppedQuality]]:
    """
    Public API: run the full vector similarity filter stage.

    Hides:
    - encoder initialization
    - filter initialization
    - index building

    Parameters:
        kg_relations:
            The retrieved subgraph relations for a given keyword.
            This subgraph is used to build the vector index.
            i.e. it is our search space here.

        qualities:
            The candidate qualities extracted from a corpus (e.g. decomposer output).
            Each quality will be treated as a query vector and its cosine similarity
            to the subgraph relation vectors will be computed.

        cfg:
            Configuration for the vector similarity filter stage.

        pretty_print:
            Whether to pretty-print the filtering results to console.
    Returns:
        (kept, dropped)
    """
    encoder = SentenceTransformerEncoder(
        model_name=cfg.encoder_model_name,
        device=cfg.encoder_device,
        normalize=cfg.normalize_embeddings,
    )

    filter = VectorSimilarityFilter(
        encoder=encoder,
        top_k=cfg.quality_to_kg_top_k,
        threshold=cfg.min_similarity_threshold,
    )

    index = filter.build_index(kg_relations)
    kept, dropped = filter.filter_qualities(index=index, qualities=qualities)

    if pretty_print:
        filter.pretty_print(kept=kept, dropped=dropped)

    return kept, dropped
