from typing import Any, List

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
