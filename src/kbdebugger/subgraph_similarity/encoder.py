from __future__ import annotations

"""
Embedding model interface + implementations.

Why this exists
---------------
The vector similarity filter needs a text encoder that maps strings -> vectors.
We keep this behind a small `TextEncoder` protocol so we can swap models easily
without touching retrieval, indexing, or filtering logic.

Implementation choices
----------------------
We provide:

1) SentenceTransformerEncoder (recommended MVP)
   - Uses `sentence-transformers` library
   - Good quality, widely used
   - Runs locally (CPU or GPU)
   - Returns float32 numpy arrays

2) DummyEncoder (testing/dev)
   - No heavy dependencies
   - Deterministic output
   - ❌ NOT semantically meaningful (only for pipeline testing)

Important note about cosine similarity
--------------------------------------
Our VectorIndex uses cosine similarity. For cosine similarity to behave well,
it is usually best to L2-normalize embeddings. SentenceTransformers supports this
directly via `normalize_embeddings=True`.
"""

from dataclasses import dataclass
from typing import Protocol, Sequence

import numpy as np
    
class TextEncoder(Protocol):
    """
    Protocol that all embedding backends must implement.

    Attributes
    ----------
    dim:
        Dimensionality of produced vectors (e.g., 384).

    Methods
    -------
    encode(texts):
        Batch-encode texts into a numpy array of shape (N, dim), dtype float32.
    """
    dim: int
    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """Encode a batch of texts into vectors (N, dim). Where N = len(texts)."""
        ...


@dataclass
class SentenceTransformerEncoder:
    """
    Local embedding encoder using the `sentence-transformers` library.

    Parameters
    ----------
    - model_name:
        HuggingFace model identifier, e.g.:
            - "sentence-transformers/all-MiniLM-L6-v2"  (fast, strong baseline)
            - "intfloat/e5-small-v2"                    (often better retrieval)
            - "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    - device:
        Where to run inference:
            - "cpu" (safe default)
            - "cuda" (if GPU available)

        If None, sentence-transformers will pick a default (often GPU if available).

    - normalize:
        If True, L2-normalize embeddings. Recommended for cosine similarity search.

    Notes
    -----
    - The first run will download model weights (unless cached).
    - This class lazily imports sentence-transformers so the package is only required
      when you actually instantiate this encoder.

    ```
    encoder = SentenceTransformerEncoder(...)
    ```
    automatically does:
    - Generate __init__ (because it's a @dataclass)
    - Run __init__
    - Then immediately run __post_init__
    """
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    device: str | None = None
    normalize: bool = True


    def __post_init__(self) -> None:
        # Lazy import so installing sentence-transformers is optional unless used.
        from sentence_transformers import SentenceTransformer  # type: ignore

        self._model = SentenceTransformer(self.model_name, device=self.device)
        
        embedding_dim = self._model.get_sentence_embedding_dimension()
        
        if embedding_dim is None:
            raise ValueError("❌ Could not determine embedding dimension from model.")
        
        self.dim = int(embedding_dim)


    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """
        Encode texts into embeddings.

        Returns
        -------
        np.ndarray
            Shape: (N, dim), dtype float32
        """
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)

        # `convert_to_numpy=True` ensures numpy output.
        # `normalize_embeddings=True` gives *unit* vectors for cosine similarity. i.e., Vector Norm ||v||_2 = 1
        vectors = self._model.encode(
            list(texts),
            batch_size=32,
            convert_to_numpy=True,
            normalize_embeddings=self.normalize,
            show_progress_bar=False,
        ) 
        # ndarray of shape (batch_size, dim), dtype=float32
        return np.asarray(vectors, dtype=np.float32)


@dataclass
class DummyEncoder:
    """
    Deterministic encoder for tests and debugging.

    ❌ This does NOT produce meaningful semantic embeddings. 
    ✅ It only allows us to test the vector index + filtering pipeline without installing ML libraries.

    Parameters
    ----------
    - dim:
        Dimensionality of the fake embeddings.
    """
    dim: int = 64

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """
        Encode texts deterministically into pseudo-random vectors based on hashing.

        Returns
        -------
        np.ndarray
            Shape: (N, dim), dtype float32, approximately unit-normalized.
        """
        out = np.zeros((len(texts), self.dim), dtype=np.float32)

        for i, t in enumerate(texts):
            # A deterministic seed per text
            seed = abs(hash(t)) % (2**32)
            rng = np.random.default_rng(seed)
            v = rng.standard_normal(self.dim).astype(np.float32)

            # Normalize so cosine behaves sensibly
            norm = float(np.linalg.norm(v)) or 1.0
            out[i] = v / norm

        return out
    
