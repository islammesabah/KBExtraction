from __future__ import annotations

"""
Batching utilities.

This module centralizes simple, deterministic batching helpers that are used across
multiple stages of the KBDebugger pipeline.

Why a project-level batching utility?
-------------------------------------
Several stages in the project benefit from processing items in fixed-size groups:

- Batched LLM decomposition (chunk -> qualities)
- Batched novelty comparison (quality -> novelty decision)
- Batched triple extraction (quality -> subject, predicate, object)
- Potential future uses:
  - batched embedding calls
  - batched retrieval / reranking

Rather than duplicating the same batching logic in multiple subpackages
(e.g., extraction/utils.py, comparator/utils.py), we keep it here to provide:

- one canonical implementation
- consistent semantics across the project
- better discoverability for future contributors

Design goals
------------
- Works on finite, indexable sequences (lists, tuples)
- Produces lists (not iterators) to make debugging easier
- Keeps behavior boring and predictable
"""

from typing import Iterator, List, Sequence, TypeVar

T = TypeVar("T")


def batched(items: Sequence[T], batch_size: int) -> Iterator[List[T]]:
    """
    Yield consecutive batches from a finite, indexable sequence.

    Parameters
    ----------
    items:
        A finite, indexable sequence (e.g., list[T], tuple[T]).
        This function intentionally does NOT accept a generic iterator/generator,
        because many debugging sessions rely on index-based slicing and the ability
        to replay logic deterministically.

    batch_size:
        Number of items per batch. Must be >= 1.

    Yields
    ------
    list[T]
        Lists of size `batch_size`, except possibly the final batch.

    Raises
    ------
    ValueError
        If `batch_size` is less than 1.

    Examples
    --------
    >>> list(batched([1, 2, 3, 4, 5], batch_size=2))
    [[1, 2], [3, 4], [5]]
    """
    if batch_size < 1:
        raise ValueError(f"batch_size must be >= 1, got {batch_size}")

    for i in range(0, len(items), batch_size):
        yield list(items[i : i + batch_size])
