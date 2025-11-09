# decompose.py (new tiny module or inline where you call it)
from __future__ import annotations
from enum import Enum
from typing import Callable, Iterable, Protocol, Any
from .sentence_decompose import build_sentence_decomposer
class DecomposeMode(str, Enum):
    SENTENCES = "sentences"
    CHUNKS = "chunks"

# class TextDecomposer(Protocol):
#     def __call__(self, text: str, /) -> list[str]: ...
# The slash '/' indicates that 'text' is a positional-only argument.
# Positional-only parameters ignore names, which sidesteps Pylance's name check.

sentence_decomposer = build_sentence_decomposer()
chunk_decomposer = lambda s: [s]  # Placeholder; replace with real chunk decomposer later.

def decompose(
    text: str,
    *,
    mode: DecomposeMode,
    # sentence_decomposer: TextDecomposer,
    # chunk_decomposer: TextDecomposer,
) -> list[str]:
    """
    Decompose `text` into atomic strings per the selected mode.
    - mode=SENTENCES: return sentence-level strings.
    - mode=CHUNKS: return chunk-level strings.
    Both `sentence_decomposer` and `chunk_decomposer` are injected callables,
    which keeps this function pure and easy to test.
    """
    if mode is DecomposeMode.SENTENCES:
        return sentence_decomposer(text)
    return chunk_decomposer(text)
