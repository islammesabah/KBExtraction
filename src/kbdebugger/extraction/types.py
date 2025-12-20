from typing import Callable
from enum import Enum

class SourceKind(str, Enum):
    TEXT = "TEXT"
    PDF_SENTENCES = "PDF_SENTENCES"
    PDF_CHUNKS = "PDF_CHUNKS"

Qualities = list[str]  # e.g., ["Transparency is a property of KI system.", ...]
TextDecomposer = Callable[[str], Qualities]

class DecomposeMode(str, Enum):
    SENTENCES = "sentences"
    CHUNKS = "chunks"
