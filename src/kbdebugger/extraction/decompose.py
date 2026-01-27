from __future__ import annotations

import os
from typing import List, Optional, Sequence, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from kbdebugger.compat.langchain import Document
from kbdebugger.extraction.utils import batched
from .sentence_to_qualities import build_sentence_decomposer
from .chunk_to_qualities import build_chunk_decomposer, build_chunk_batch_decomposer
from .types import Qualities, TextDecomposer, BatchTextDecomposer, DecomposeMode
from .logging import save_qualities_json

# ---------------------------------------------------------------------------
# Module-level decomposer singletons
# ---------------------------------------------------------------------------
# These are initialized once at import time to avoid re-loading prompt resources
# and few-shot examples repeatedly inside tight loops.
_sentence_to_qualities_decomposer: TextDecomposer = build_sentence_decomposer()
_chunk_to_qualities_decomposer: TextDecomposer = build_chunk_decomposer()
_chunk_batch_to_qualities_decomposer: BatchTextDecomposer = build_chunk_batch_decomposer()


def decompose(
    text: str,
    *,
    mode: DecomposeMode
) -> Qualities:
    """
    Decompose a single input text into "qualities" under the selected mode.

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
        A list of short, atomic sentences (qualities).
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


def _decompose_one_batch(
    batch_id: int,
    group: List[str],
) -> Tuple[int, List[Qualities]]:
    """
    Worker wrapper for parallel batch decomposition.

    Returns
    -------
    (batch_id, batch_results)
        batch_id is used to optionally re-order results deterministically.
    """
    return batch_id, _chunk_batch_to_qualities_decomposer(group)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def decompose_documents(
    docs: Sequence[Document],
    *,
    mode: DecomposeMode,
    batch_size: int = 4,
    use_batch_decomposer: bool = True,
    parallel: bool = False,
    max_workers: Optional[int] = 2,
) -> Qualities:
    """
    Decompose a list of LangChain Documents into a flat list of qualities.

    This is the *second stage* of the Extractor pipeline:
        INPUT: Document chunks
        OUTPUT: atomic qualities (decomposer LLM)

    🚀 Performance rationale
    ---------------------
    Decomposing one chunk per LLM call scales poorly for realistic PDFs.
    When `mode == DecomposeMode.CHUNKS`, this function can use a batched decomposer
    to reduce LLM round-trips by processing multiple chunks per call.


    Parameters
    ----------
    docs:
        Chunked LangChain Documents produced by the chunker stage.

    mode:
        How to interpret each doc.page_content for decomposition (sentences vs chunks).

    batch_size:
        Number of chunk texts to send per LLM request when batching is enabled.
        Typical values: 3-8. Start at 5.
    
    use_batch_decomposer:
        If True and `mode == DecomposeMode.CHUNKS`, use the batched decomposer.
        If False, always fall back to single-text decomposition.

    Returns
    -------
    Qualities:
        A flat list of atomic qualities produced across the entire corpus.


    Notes
    -----
    - The batch decomposer returns `List[Qualities]` aligned to the input order.
      We flatten it here because the rest of the pipeline expects a flat list.
    - Missing or malformed per-chunk outputs are handled inside the batch decomposer
      (yielding empty lists), so this function remains robust.
    """
    all_qualities: Qualities = []

    if not docs:
        # Save empty output for consistent downstream behavior / debugging.
        meta: dict[str, Any] = {
            "mode": mode,
            "num_docs": 0,
            "use_batch_decomposer": use_batch_decomposer,
            "batch_size": batch_size,
        }
        save_qualities_json(qualities=all_qualities, meta=meta, mode=mode)
        return all_qualities
    
    # Extract texts once for easier batching and consistent behavior.
    texts: List[str] = [getattr(doc, "page_content", "") for doc in docs]
    
    # --- Fast path: batched chunk decomposition ---
    if mode == DecomposeMode.CHUNKS and use_batch_decomposer:
        # groups is a list of lists of chunk texts.
        # e.g. Each list has length == batch_size, except possibly the last one.
        groups = list(batched(texts, batch_size=batch_size))

        # Parallelism is optional; keep it controlled.
        if parallel:
            # Submit all groups but limit concurrency by max_workers.
            results_by_batch: dict[int, List[Qualities]] = {}

            # with ThreadPoolExecutor(max_workers=max_workers) as pool:
            #     futures = [
            #         pool.submit(_decompose_one_batch, i, group)
            #         for i, group in enumerate(groups)
            #     ]

            #     for fut in as_completed(futures):
            #         try:
            #             batch_id, batch_results = fut.result()
            #             results_by_batch[batch_id] = batch_results
            #         except Exception as e:
            #             print(f"Error in batch decomposition: {e}")
            #             results_by_batch[batch_id] = []   # but we need batch_id: so store it in closure
                    
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                future_to_batch_id: dict[Any, int] = {}

                for i, group in enumerate(groups):
                    fut = pool.submit(_decompose_one_batch, i, group)
                    future_to_batch_id[fut] = i

                for fut in as_completed(future_to_batch_id):
                    batch_id = future_to_batch_id[fut]
                    try:
                        _, batch_results = fut.result()
                        results_by_batch[batch_id] = batch_results
                    except Exception as e:
                        print(f"[decompose_documents] Batch {batch_id} failed: {e}")
                        # Preserve alignment: return empty per-chunk outputs for that batch
                        results_by_batch[batch_id] = [[] for _ in groups[batch_id]]



            # Flatten in deterministic order (0..N-1) regardless of completion order
            for i in range(len(groups)):
                for qualities in results_by_batch.get(i, []):
                    all_qualities.extend(qualities)

        else:
            for group in groups:
                group_results: List[Qualities] = _chunk_batch_to_qualities_decomposer(group)
                # Flatten group results into the global list.
                for qualities in group_results:
                    all_qualities.extend(qualities)

        meta: dict[str, Any] = {
            "mode": mode,
            "num_docs": len(docs),
            "use_batch_decomposer": True,
            "batch_size": batch_size,
            "num_batches": (len(docs) + batch_size - 1) // batch_size,
            "parallel": parallel,
            "max_workers": max_workers if parallel else None,
        }
        save_qualities_json(qualities=all_qualities, meta=meta, mode=mode)
        return all_qualities
    

    # --- Default path: one document -> one decompose() call ---
    for text in texts:
        qualities = decompose(text, mode=mode)
        all_qualities.extend(qualities)

    meta: dict[str, Any] = {
        "mode": mode,
        "num_docs": len(docs),
        "use_batch_decomposer": False,
        "batch_size": None,
    }
    save_qualities_json(qualities=all_qualities, meta=meta, mode=mode)

    return all_qualities
