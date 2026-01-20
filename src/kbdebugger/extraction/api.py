from __future__ import annotations

from .chunk import chunk_corpus
from .decompose import decompose_documents
from .types import Qualities, SourceKind


def extract_qualities_from_corpus(
    *,
    source_kind: SourceKind,
    path: str,
) -> Qualities:
    """
    Public API: end-to-end quality extraction from a corpus.
    """
    docs, mode = chunk_corpus(source_kind=source_kind, path=path)
    qualities = decompose_documents(docs=docs, mode=mode)

    if not qualities:
        raise ValueError("Decomposition produced no qualities.")
    return qualities
