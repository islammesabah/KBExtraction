from __future__ import annotations

from enum import Enum

from rpds import List

from .sentence_decompose import build_sentence_decomposer
from .chunk_decompose import build_chunk_decomposer
from .types import Qualities, TextDecomposer
from typing import List

class DecomposeMode(str, Enum):
    SENTENCES = "sentences"
    CHUNKS = "chunks"


# Build default decomposers once at import time.
# These are module-level singletons; if we ever want to swap them (e.g. for tests),
# we can reassign _sentence_decomposer / _chunk_decomposer.
_sentence_decomposer: TextDecomposer = build_sentence_decomposer()
_chunk_decomposer: TextDecomposer = build_chunk_decomposer()

def decompose(
    text: str,
    *,
    mode: DecomposeMode,
) -> List[str]:
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
            return _sentence_decomposer(text)
        case DecomposeMode.CHUNKS:
            return _chunk_decomposer(text)
        case _:
            pass
        
    # Defensive: this should never happen with the Enum, but keeps mypy happy
    raise ValueError(f"Unsupported DecomposeMode: {mode}")