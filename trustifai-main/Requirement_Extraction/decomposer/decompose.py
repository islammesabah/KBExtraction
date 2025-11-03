# decompose.py (new tiny module or inline where you call it)
from __future__ import annotations
from enum import Enum
from typing import Callable, Iterable, Protocol, Any

class DecomposeMode(str, Enum):
    SENTENCES = "sentences"
    CHUNKS = "chunks"

class TextDecomposer(Protocol):
    def __call__(self, text: str) -> list[str]: ...

def decompose(
    text: str,
    *,
    mode: DecomposeMode,
    sentence_decomposer: TextDecomposer,
    chunk_decomposer: TextDecomposer,
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
