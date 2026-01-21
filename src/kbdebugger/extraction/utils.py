import re
from typing import Any, Iterator, List, Optional, Sequence, TypeVar

from kbdebugger.types import ExtractionResult, TripletSOP
from kbdebugger.utils.json import now_utc_compact, write_json
from .types import Qualities
from typing import Any, Dict


def coerce_triplets(item: Dict[str, Any], fallback_sentence: str) -> ExtractionResult:
    """
    Coerce a single item dict to ExtractionResult:
    { "sentence": str, "triplets": list[TripletSOP] }
    """
    sentence = item.get("sentence", fallback_sentence)
    raw_triplets = item.get("triplets", [])
    triplets: list[TripletSOP] = []

    if isinstance(raw_triplets, list):
        for t in raw_triplets:
            if isinstance(t, (list, tuple)) and len(t) == 3:
                subj, obj, rel = t
                if all(isinstance(x, str) for x in (subj, obj, rel)):
                    triplets.append((subj.strip(), obj.strip(), rel.strip()))

    return {"sentence": str(sentence), "triplets": triplets}


def coerce_triplets_batch(obj: Dict[str, Any], sentences: List[str]) -> List[ExtractionResult]:
    """
    Coerce the LLM batch output of shape:
    {
      "triplets_batch": [
        {"id": 0, "sentence": "...", "triplets": [...]},
        ...
      ]
    }
    into a list[ExtractionResult], aligned by input index.
    """
    # Default: one empty result per input sentence
    empty: ExtractionResult = {"sentence": "", "triplets": []}
    results: List[ExtractionResult] = [empty for _ in sentences]

    batch = obj.get("triplets_batch", [])
    if not isinstance(batch, list):
        return results

    # Map by id, but also be robust
    for item in batch:
        if not isinstance(item, dict):
            continue

        idx = item.get("id")
        if isinstance(idx, int) and 0 <= idx < len(sentences):
            results[idx] = coerce_triplets(item, sentences[idx])

    # Fill any missing entries with fallback (no triplets)
    for i, res in enumerate(results):
        if res["sentence"] == "":
            results[i] = {"sentence": sentences[i], "triplets": []}

    return results


def coerce_qualities(obj: Dict) -> Qualities:
    if not isinstance(obj, dict):
        return []
    qualities = obj.get("qualities")
    if not isinstance(qualities, list):
        return []
    out: Qualities = []
    for q in qualities:
        if isinstance(q, str):
            s = q.strip()
            if s:
                out.append(s)
    return out


def save_results_json(results: List[ExtractionResult]) -> None:
    """
    Write extraction results to a JSON file.
    """
    created_at = now_utc_compact()
    data = {
        "results": results,
    }
    path = f"logs/05_triplet_extraction_results_{created_at}.json"
    write_json(path, data)
    print(f"\n[INFO] Wrote JSON results to {path}")


# ---------------------------------------------------------------------------
# Helpers for `build_chunk_batch_decomposer`
# ---------------------------------------------------------------------------
_WS_RE = re.compile(r"\s+") # this matches all whitespace sequences i.e. newlines, tabs, multiple spaces, etc.

def sanitize_chunk(text: str) -> str:
    """
    Normalize a chunk into a single-line string.

    We intentionally avoid aggressive cleaning here: the upstream PDF cleaning
    stage already handles boilerplate/DOI stripping etc. Our goal is only to
    prevent formatting artifacts from confusing the LLM.
    """
    # replace all whitespace sequences (newlines, tabs, multiple spaces) with single space " "
    return _WS_RE.sub(" ", text or "").strip()


def coerce_batch_qualities(
    obj: Any,
    *,
    expected_n: int,
) -> Dict[int, Qualities]:
    """
    Parse the JSON object returned by the batch prompt into an id->qualities map.

    Expected schema (strict, by prompt contract):
        {
          "results": [
            {"id": 0, "qualities": ["...", "..."]},
            {"id": 1, "qualities": []}
          ]
        }

    This parser is defensive:
    - Accepts "id" as int or numeric string.
    - Accepts "qualities" as list[str] or other coercible structures.
    - Ignores unknown items; only keeps ids within range.
    - Returns a possibly sparse mapping; caller fills missing ids with [].
    """
    if not isinstance(obj, dict):
        return {}

    results = obj.get("results")
    if not isinstance(results, list):
        return {}

    out: Dict[int, Qualities] = {}

    for item in results:
        if not isinstance(item, dict):
            continue

        raw_id = item.get("id")
        if raw_id is None:
            continue

        # Coerce id -> int if possible
        chunk_id: Optional[int] = None
        if isinstance(raw_id, int):
            chunk_id = raw_id
        elif isinstance(raw_id, str) and raw_id.strip().isdigit():
            chunk_id = int(raw_id.strip())

        if chunk_id is None:
            continue
        if chunk_id < 0 or chunk_id >= expected_n:
            continue

        raw_qualities = item.get("qualities", [])
        # Try to coerce qualities robustly.
        # - If it's already a list, keep string-like entries.
        # - If it's a dict (rare), attempt coerce_qualities on it.
        qualities: Qualities = []

        if isinstance(raw_qualities, list):
            qualities = [str(x).strip() for x in raw_qualities if str(x).strip()]
        else:
            # Some models might accidentally return {"qualities": [...]} per item.
            # coerce_qualities can often salvage this.
            try:
                qualities = coerce_qualities(raw_qualities)  # type: ignore[arg-type]
            except Exception:
                qualities = []

        out[chunk_id] = qualities

    return out


T = TypeVar("T")


def batched(items: Sequence[T], batch_size: int) -> Iterator[List[T]]:
    """
    Yield consecutive batches from a sequence.

    Parameters
    ----------
    items:
        A finite, indexable sequence.
    batch_size:
        Number of items per batch. Must be >= 1.

    Yields
    ------
    list[T]
        Lists of size `batch_size`, except possibly the final batch.

    Notes
    -----
    We keep this in pure-Python (no itertools recipes) for readability and to
    avoid surprising behavior with iterators/generators in debugging sessions.
    """
    if batch_size < 1:
        raise ValueError(f"batch_size must be >= 1, got {batch_size}")

    for i in range(0, len(items), batch_size):
        yield list(items[i : i + batch_size])

