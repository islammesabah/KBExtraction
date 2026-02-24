# kbdebugger/vector/index_faiss.py
# -----------------------------------------------------------------------------
# Vector index implementation using Facebook AI Similarity Search (FAISS).
# -----------------------------------------------------------------------------
from __future__ import annotations

"""
Facebook AI Similarity Search (FAISS) vector index backend.

What this module is
-------------------
This file provides an in-process, in-memory vector index for nearest-neighbor search
over embedding vectors using **Facebook AI Similarity Search (FAISS)**.

FAISS is a widely used library (C++ with Python bindings) for efficient similarity
search and clustering of dense vectors. It supports multiple index types, ranging from
exact search to approximate nearest neighbor (ANN) search. In this project we start
with an **exact** index because our indexed set is typically small (a retrieved
Neo4j subgraph), and we want maximum stability and determinism.

Why we are replacing HNSWLIB
----------------------------
We previously used `hnswlib` (Hierarchical Navigable Small World library), which can
be compiled with CPU instruction set extensions such as AVX-512. On cluster nodes that
do not support these instructions, calling into the extension may crash the process
with "Illegal instruction (core dumped)".

FAISS CPU wheels are generally more stable across heterogeneous compute environments.
(If you later run into similar issues with FAISS on our cluster, you can still fall
back to a pure NumPy brute-force backend, but FAISS is a strong default.)

Similarity metric: cosine similarity (not distance)
---------------------------------------------------
Downstream parts of KBDebugger expect **cosine similarity scores** in [approximately -1, 1]
(usually [0, 1] for many embedding models) where **higher means more similar**.

FAISS provides indices that operate on:
- L2 distance (Euclidean), or
- inner product (dot product)

We implement cosine similarity by:
1) **L2-normalizing** all vectors (both indexed vectors and query vectors)
2) Using an **inner product index**
   because for unit-normalized vectors:

        cosine_similarity(u, v) == dot(u, v)

Index type used here
--------------------
We use `faiss.IndexFlatIP`, which is:
- "Flat" = brute-force exact search (no approximation)
- "IP"   = Inner Product similarity

This is simple, deterministic, and extremely reliable.

If you later want approximate search (for huge indexes), FAISS also supports IVF,
HNSW, PQ, etc., but this MVP intentionally keeps things straightforward.

Public API compatibility
------------------------
This module is designed to mirror the old `VectorIndex` API:

- `create(dim=..., max_elements=...)`
- `add(vectors, items)`
- `search(query_vec, k)`
- `search_batch(query_vecs, k)`

The most important is `search_batch`, since our pipeline uses batched search to
avoid Python loops.

Dependencies
------------
- numpy
- faiss (Python package name is typically: `faiss-cpu`)

Important note: payload mapping
-------------------------------
FAISS stores only vectors. We maintain a parallel Python list called `payloads`
where:

    payloads[i] == domain object associated with vector ID i

FAISS returns neighbor IDs; we map IDs back to payload objects for callers.

"""

from dataclasses import dataclass
from typing import Generic, List, Sequence, Tuple, TypeVar

import numpy as np
from .faiss_utils import (
    _as_float32_matrix,
    _as_float32_vector,
    _l2_normalize_rows,
)

# Generic payload type: each vector is associated with an arbitrary Python object.
T = TypeVar("T")


@dataclass
class VectorIndex(Generic[T]):
    """
    In-memory vector index using Facebook AI Similarity Search (FAISS).

    Attributes
    ----------
    dim:
        Dimensionality of the embedding vectors.

    index:
        The underlying FAISS index instance (IndexFlatIP).

    payloads:
        List mapping internal vector IDs -> domain objects.
        The internal vector ID used by FAISS equals the position in this list.
    """

    dim: int
    index: "faiss.Index"  # type: ignore 
                          # quoted annotation to avoid importing faiss at module import time
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
    ) -> "VectorIndex[T]":
        """
        Create and initialize a new FAISS-based vector index.

        Parameters
        ----------
        dim:
            Dimensionality of embedding vectors (must match encoder output).

        max_elements:
            Maximum number of vectors expected to be added.
            This parameter is kept for API compatibility with the previous HNSWLIB index.
            It is not required by IndexFlatIP, because IndexFlatIP grows dynamically.

        Returns
        -------
        VectorIndex[T]
            An empty vector index ready to accept vectors.

        Notes
        -----
        We intentionally use an exact index (IndexFlatIP) for stability and simplicity.

        - "Flat" means brute-force exact search. i.e. no approximation, no clustering, no quantization of vectors.
        - "IP" stands for Inner Product.
        - We convert inner product to cosine similarity by L2-normalizing vectors.

        Even though `max_elements` is not required by FAISS here, we keep it so the
        call sites do not change and future backends can use it if needed.
        """
        # Lazy import: faiss is only required when you actually instantiate an index.
        import faiss  # type: ignore

        # Exact inner-product index. With L2-normalized vectors, this returns cosine similarity.
        idx = faiss.IndexFlatIP(dim)

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
            Example payload types:
              - GraphRelation objects
              - string identifiers
              - any Python object we want to retrieve for nearest neighbors

        Raises
        ------
        ValueError
            If shapes mismatch or the number of vectors differs from number of items.

        Implementation details
        ----------------------
        - FAISS expects float32 contiguous arrays.
        - We L2-normalize vectors before adding them so that inner product == cosine similarity.
        - The FAISS internal IDs are assigned in insertion order: 0..N-1 for the first add(),
          then continuing  N.. for subsequent add() calls.
        - We mirror that by extending `payloads` in the same order.
        """
        matrix = _as_float32_matrix(vectors, name="vectors")

        if matrix.shape[1] != self.dim:
            raise ValueError(
                f"❌ Shape mismatch: expected vectors of shape (N, {self.dim}), got {matrix.shape}"
            )

        if len(matrix) != len(items):
            raise ValueError("❌ Number of vectors must match number of payload items.")

        # Normalize vectors so dot product equals cosine similarity.
        matrix_normalized = _l2_normalize_rows(matrix) # keeps shape (N, dim)

        # Add to FAISS index.
        self.index.add(matrix_normalized)

        # Preserve payload mapping (ID -> object).
        self.payloads.extend(list(items))

    # ------------------------------------------------------------------
    # Search (single query)
    # ------------------------------------------------------------------
    def search(self, query_vec: np.ndarray, k: int) -> List[Tuple[T, float]]:
        """
        Search for the k nearest neighbors of a single query vector.

        Parameters
        ----------
        query_vec:
            Query vector of shape (dim,).

        k:
            Number of nearest neighbors to retrieve.

        Returns
        -------
        List[Tuple[T, float]]
            List of (payload, similarity_score) pairs, where:
              - payload is the domain object mapped to the neighbor vector
              - similarity_score is cosine similarity (higher = more similar)

        Notes
        -----
        This is a convenience wrapper around `search_batch` for a single query.
        For performance, prefer `search_batch` when you have many queries.
        """
        if k <= 0:
            return []

        q = _as_float32_vector(query_vec, dim=self.dim, name="query_vec").reshape(1, -1)
        neighbors, scores = self.search_batch(q, k=k)

        # neighbors is length 1 list; scores is shape (1, k)
        out: List[Tuple[T, float]] = []
        row_neighbors = neighbors[0]
        row_scores = scores[0]

        # Align by min length because neighbor list may be shorter if index is small.
        # e.g., k = 5 but index only has 3 vectors, so FAISS returns 3 neighbors + 2 invalid (-1) IDs.
        n = min(len(row_neighbors), int(row_scores.shape[0]))
        for i in range(n):
            out.append((row_neighbors[i], float(row_scores[i])))

        return out

    # ------------------------------------------------------------------
    # Search (batched queries)
    # ------------------------------------------------------------------
    def search_batch(self, query_vecs: np.ndarray, k: int) -> Tuple[
        List[List[T]], 
        np.ndarray
    ]:
        """
        Perform a **batched** cosine-similarity search over the index.

        This is the equivalent of calling `search()` in a loop, but it avoids
        Python overhead by doing one FAISS call for all queries.

        Parameters
        ----------
        query_vecs:
            NumPy array of shape (Q, dim) containing Q query embedding vectors.

        k:
            Number of nearest neighbors to retrieve **per query**.

        Returns
        -------
        (neighbors, scores):
            neighbors:
                Python list of length Q.
                Each entry is a list of payload objects (length up to k),
                representing the nearest neighbors for that query.

            scores:
                NumPy float32 array of shape (Q, k) containing cosine similarity
                scores aligned with the neighbor IDs returned by FAISS.

        Notes
        -----
        - We return cosine similarity scores because we:
            1) L2-normalize indexed vectors during `add()`
            2) L2-normalize query vectors here
            3) use FAISS IndexFlatIP (inner product)

        - FAISS returns:
            - `scores`: inner products (cosine similarity due to normalization), shape (Q, k)
            - `ids`: neighbor indices, shape (Q, k), where ids[i, j] is the vector ID

        - If the index has fewer than k vectors, FAISS still returns arrays of shape (Q, k),
          but some IDs may be -1. We:
            - omit payloads for -1 IDs
            - set the corresponding scores to 0.0 to keep thresholding deterministic
        """
        q = _as_float32_matrix(query_vecs, name="query_vecs") # shape (Q, dim)

        if q.shape[1] != self.dim:
            raise ValueError(
                f"❌ Shape mismatch: expected query_vecs of shape (Q, {self.dim}), got {q.shape}"
            )

        num_q = int(q.shape[0]) # number of query vectors

        if k <= 0:
            return ([[] for _ in range(num_q)], np.zeros((num_q, 0), dtype=np.float32))

        # Normalize query vectors so dot product equals cosine similarity.
        q_norm = _l2_normalize_rows(q)

        # FAISS expects contiguous float32 arrays.
        q_norm = np.ascontiguousarray(q_norm, dtype=np.float32)

        # Perform batched search.
        # scores: (Q, k) float32
        # ids:    (Q, k) int64; id == -1 indicates invalid neighbor (not enough vectors)
        scores, ids = self.index.search(q_norm, k)

        scores = np.asarray(scores, dtype=np.float32)
        ids = np.asarray(ids, dtype=np.int64)

        neighbors: List[List[T]] = []
        for row_ids in ids:
            # row_ids is shape (k,) containing the IDs of the top-k neighbors for this query vector.
            row_payloads: List[T] = []
            for idx in row_ids:
                if idx < 0:
                    continue
                # Map FAISS vector ID -> payload
                row_payloads.append(self.payloads[int(idx)])

            # Now for this specific query vector, we have a list of payloads corresponding to the top-k neighbors. 
            # Append to the overall neighbors list.                
            neighbors.append(row_payloads)

        # Ensure scores for invalid IDs are exactly 0.0 (deterministic thresholding).
        invalid_mask = ids < 0
        if np.any(invalid_mask):
            scores = scores.copy()
            scores[invalid_mask] = 0.0

        return neighbors, scores
