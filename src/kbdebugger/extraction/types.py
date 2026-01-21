from typing import Callable, List
from enum import Enum

class SourceKind(str, Enum):
    TEXT = "TEXT"
    PDF_SENTENCES = "PDF_SENTENCES"
    PDF_CHUNKS = "PDF_CHUNKS"

Qualities = list[str]  # e.g., ["Transparency is a property of KI system.", ...]
TextDecomposer = Callable[[str], Qualities] # e.g., decompose("some text") -> ["quality1", "quality2", ...]
BatchTextDecomposer = Callable[[List[str]], List[Qualities]] # e.g., decompose_batch(["text1", "text2"]) -> [["quality1", ...], ["qualityA", ...]]

class DecomposeMode(str, Enum):
    SENTENCES = "sentences"
    CHUNKS = "chunks"
