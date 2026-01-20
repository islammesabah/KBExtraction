from __future__ import annotations

import os
from typing import Optional, Sequence, Any

from kbdebugger.compat.langchain import Document
from .sentence_to_qualities import build_sentence_decomposer
from .chunk_to_qualities import build_chunk_decomposer
from .types import Qualities, TextDecomposer, DecomposeMode
from .logging import save_qualities_json

# Build default decomposers once at import time.
# These are module-level singletons; if we ever want to swap them (e.g. for tests),
# we can reassign.
_sentence_to_qualities_decomposer: TextDecomposer = build_sentence_decomposer()
_chunk_to_qualities_decomposer: TextDecomposer = build_chunk_decomposer()

def decompose(
    text: str,
    *,
    mode: DecomposeMode
) -> Qualities:
    """
    Decompose `text` into atomic strings per the selected mode.

    Parameters
    ----------
    text:
        Input text: either a single sentence or a larger chunk.
    mode:
        - DecomposeMode.SENTENCES:
            Use when `text` is already sentence-like but may contain
            multiple atomic statements that should be split.
            Example:
                "The cat sat on the mat and looked at the dog."
                → ["The cat sat on the mat.", "The cat looked at the dog."]

        - DecomposeMode.CHUNKS:
            Use when `text` is a larger paragraph or chunk and you want to
            extract key qualities / statements.
            Example:
                "Cats are great pets. They are independent and curious animals..."
                → ["Cats are great pets.",
                   "Cats are independent animals.",
                   "Cats are curious animals."]

    Returns
    -------
    list[str]
        A list of short, atomic sentences/qualities.
    """
    match mode:
        case DecomposeMode.SENTENCES:
            return _sentence_to_qualities_decomposer(text)
        case DecomposeMode.CHUNKS:
            return _chunk_to_qualities_decomposer(text)
        case _:
            pass

    # Defensive: this should never happen with the Enum, but keeps mypy happy
    raise ValueError(f"Unsupported DecomposeMode: {mode}")


def decompose_documents(
    docs: Sequence[Document],
    *,
    mode: DecomposeMode,
) -> Qualities:
    """
    Decompose a list of LangChain Documents into a flat list of qualities.

    This is the *second stage* of the Extractor pipeline:
        INPUT: Document chunks -> OUTPUT: atomic qualities (decomposer LLM)


    Parameters
    ----------
    docs:
        Chunked LangChain Documents produced by the chunker stage.

    mode:
        How to interpret each doc.page_content for decomposition (sentences vs chunks).

    log_path:
        If provided, writes the final qualities list to a JSON file.
        If None, uses a default path under logs/.

    Returns
    -------
    Qualities:
        Flat list of atomic sentences produced across the entire corpus.
    """
    all_qualities: Qualities = []

    for doc in docs:
        text = getattr(doc, "page_content", "")
        qualities = decompose(text, mode=mode)
        all_qualities.extend(qualities)


    # Include small but useful metadata for demos and debugging
    meta: dict[str, Any] = {
        "mode": mode,
        "num_docs": len(docs),
    }

    # Let the save function handle directory creation
    save_qualities_json(qualities=all_qualities, meta=meta, mode=mode)

    return all_qualities
