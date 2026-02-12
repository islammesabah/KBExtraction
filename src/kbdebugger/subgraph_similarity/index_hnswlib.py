# vector index abstraction + HNSW (Hierarchical Navigable Small World) backend.
# (HNSW-based in-memory vector index — documented MVP)
from __future__ import annotations

"""
Vector index abstraction for approximate nearest-neighbor (ANN) search.

This module provides a thin, well-documented wrapper around `hnswlib`,
which implements the HNSW (Hierarchical Navigable Small World) graph
algorithm for fast cosine-similarity search in high-dimensional spaces.

Why HNSW?
---------
- Very fast approximate nearest-neighbor search
- Excellent recall/latency tradeoff
- No server required (in-process)
- Ideal for *ephemeral* indexes such as:
    - KG subgraph context
    - per-query similarity filtering
    - MVP experimentation

This index is **NOT** a database.
It is rebuilt from scratch per retrieval run (by design).
"""

from dataclasses import dataclass
from typing import Generic, TypeVar, Sequence, List, Tuple

import numpy as np
import hnswlib

# Generic payload type:
# each vector is associated with an arbitrary Python object
T = TypeVar("T")

@dataclass
class VectorIndex(Generic[T]):
    """
    In-memory vector index using cosine similarity.

    Attributes
    ----------
    dim:
        Dimensionality of the embedding vectors.

    index:
        The underlying hnswlib.Index instance.

    payloads:
        A list mapping internal vector IDs -> domain objects
        (e.g., GraphRelation instances).
    """

    dim: int
    index: hnswlib.Index
    payloads: List[T]

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    @classmethod
    def create(
        cls,
        *,
        dim: int,
        max_elements: int,
        ef_construction: int = 200,
        M: int = 16,
        ef_search: int = 50,
    ) -> VectorIndex[T]:
        """
        Create and initialize a new HNSW vector index.

        Parameters
        ----------
        - dim:
            Dimensionality of the embedding vectors
            (must match the output size of our encoder).

        - max_elements:
            Maximum number of vectors that will be added to this index.
            For our use case, this is typically:
                len(subgraph_relations)

        - ef_construction:
            Controls index *construction quality* vs build time.

            - Higher values → 😀⬆️ better recall, ☹️⏳️ slower index build
            - Lower values  → 😀⏳️ faster build,  ☹️⬇️ lower recall

            Rule of thumb:
                100-400 is reasonable for most NLP embeddings.

            We default to 200 because:
                - subgraph size is moderate
                - build happens infrequently
                - we prefer recall over micro-optimizations

        - M:
            Maximum number of connections per node in the HNSW graph.

            - Higher values → 😀⬆️ better accuracy, ☹️🧠 more memory
            - Lower values → 😀🧠 smaller index, ☹️⬇️ slightly worse recall

            Typical values:
                8-32

            We default to 16 (balanced, widely used).

        - ef_search:
            Controls *search-time* accuracy vs latency.

            - Higher → 😀⬆️ more accurate but ☹️⏳️ slower queries
            - Must be >= k (number of neighbors we request)

            We default to 50, which is plenty for k≈5-10.

        Returns
        -------
        VectorIndex[T]
            An empty, initialized vector index ready to accept vectors.
        """
        # Create index for cosine similarity
        # Note: hnswlib uses cosine *distance* internally
        idx = hnswlib.Index(space="cosine", dim=dim)

        # Initialize index memory and graph structure
        idx.init_index(
            max_elements=max_elements,
            ef_construction=ef_construction,
            M=M,
        )

        # Set search-time parameter (can be adjusted later)
        idx.set_ef(ef_search)

        return cls(dim=dim, index=idx, payloads=[])

    # ------------------------------------------------------------------
    # Insertion
    # ------------------------------------------------------------------
    def add(self, vectors: np.ndarray, items: Sequence[T]) -> None:
        """
        Add vectors and their associated payload objects to the index.

        Parameters
        ----------
        vectors:
            NumPy array of shape (N, dim) containing embedding vectors.

        items:
            Sequence of domain objects (length N) associated with vectors.
            Example:
                - GraphRelation objects
                - IDs
                - Any metadata you want to retrieve later

        Notes
        -----
        Internally, hnswlib assigns each vector an integer ID.
        We map these IDs to `payloads` so search results can be
        returned as domain objects instead of raw indices.
        """
        vectors = np.asarray(vectors, dtype=np.float32)

        if vectors.ndim != 2 or vectors.shape[1] != self.dim:
            raise ValueError(
                f"❌ Shape Missmatch: Expected vectors of shape (N, {self.dim}), "
                f"got {vectors.shape}"
            )

        if len(vectors) != len(items):
            raise ValueError(
                "❌ Number of vectors must match number of payload items"
            )

        start_id = len(self.payloads) # Next available internal ID
        # Create sequential IDs for new vectors to be added to the index
        ids = np.arange(start_id, start_id + len(items))

        self.index.add_items(vectors, ids)
        self.payloads.extend(items)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def search(self, query_vec: np.ndarray, k: int) -> List[Tuple[T, float]]:
        """
        Perform a cosine-similarity search over the index.

        Parameters
        ----------
        query_vec:
            Embedding vector of shape (dim,).

        k:
            Number of nearest neighbors to retrieve.

        Returns
        -------
        List[Tuple[T, float]]
            A list of (payload, similarity_score) pairs, where:

            - payload is the associated domain object
            - similarity_score ∈ [0, 1], higher is more similar

        Notes
        -----
        hnswlib returns *cosine distance*:
            distance = 1 - cosine_similarity

        We convert it back to cosine similarity here so downstream
        code never has to think about distance metrics.
        """
        if k <= 0:
            return []

        # Force 1D shape (1, dim) & float32 because hnswlib requires it
        q = np.asarray(query_vec, dtype=np.float32).reshape(1, -1) 

        labels, distances = self.index.knn_query(q, k=k)
        # - labels: 
        # type: NDArray[uint64] 
        # shape: (1, k) of internal vector IDs. 
        #        i.e., raw indices of the nearest neighbors.
        #        We map these to payloads below.
        # 
        # - distances: 
        # type: NDArray[float32] 
        # shape: (1, k) of cosine distances

        results: List[Tuple[T, float]] = []

        for idx, dist in zip(labels[0], distances[0]):
            # idx is the internal vector ID
            # idx can be -1 if not enough neighbors found
            if idx < 0:
                continue

            similarity = 1.0 - float(dist)
            # Map internal ID to payload object
            payload = self.payloads[int(idx)]
            results.append((payload, similarity))

        return results


    def search_batch(self, query_vecs: np.ndarray, k: int) -> Tuple[List[List[T]], np.ndarray]:
        """
        Perform a batch cosine-similarity search over the index.

        This is the vectorized / "matrix mindset" equivalent of calling `search()`
        in a Python loop, and is typically *much* faster when you have many queries
        (e.g., 1000+ qualities), because it reduces Python-to-hnswlib overhead to
        a single call.

        Parameters
        ----------
        query_vecs:
            NumPy array of shape (Q, dim) containing Q query embedding vectors.

        k:
            Number of nearest neighbors to retrieve per query.

        Returns
        -------
        (neighbors, scores):
            neighbors:
                A Python list of length Q; each entry is a list of payload objects
                (length up to k) corresponding to the nearest neighbors.

            scores:
                A float32 NumPy array of shape (Q, k) with cosine similarity scores
                in [0, 1], aligned with `neighbors`.

        Notes
        -----
        - hnswlib returns cosine *distance*: dist = 1 - cosine_similarity
          We convert to cosine similarity via: sim = 1 - dist.
        - hnswlib may return label -1 when it cannot return k neighbors.
          In that case, we keep a score of 0.0 and do not add a payload.
        - For performance, we always convert inputs to contiguous float32.
        """
        if k <= 0:
            # Return an empty neighbor list per query, and an empty score matrix.
            q = np.asarray(query_vecs)
            num_q = int(q.shape[0]) if q.ndim == 2 else 0
            return ([[] for _ in range(num_q)], np.zeros((num_q, 0), dtype=np.float32))

        # Ensure contiguous float32 array
        q = np.ascontiguousarray(np.asarray(query_vecs, dtype=np.float32))

        if q.ndim != 2 or q.shape[1] != self.dim:
            raise ValueError(
                f"❌ Shape Missmatch: Expected query_vecs of shape (Q, {self.dim}), got {q.shape}"
            )

        labels, distances = self.index.knn_query(q, k=k)
        # labels:    (Q, k) int64/uint64 (internal IDs, -1 if missing)
        # distances: (Q, k) float32 cosine distances

        # Convert distance -> similarity (vectorized).
        # If label == -1, distance can be garbage; we'll mask below.
        scores = (1.0 - distances).astype(np.float32, copy=False)

        neighbors: List[List[T]] = []
        for row_labels in labels:
            row_payloads: List[T] = []
            for idx in row_labels:
                if idx < 0:
                    # Not enough neighbors; skip adding payload.
                    continue
                row_payloads.append(self.payloads[int(idx)])
            neighbors.append(row_payloads)

        # Ensure that scores for invalid (-1) labels are 0.0 for safety.
        # (This makes thresholding deterministic.)
        invalid_mask = labels < 0
        if np.any(invalid_mask):
            scores = scores.copy()
            scores[invalid_mask] = 0.0

        return neighbors, scores

