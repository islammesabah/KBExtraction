from typing import Any, List

from kbdebugger.types import ExtractionResult, TripletSOP
from .types import Qualities
from typing import Any, Dict

# def coerce_triplets(obj: Any, sentence: str) -> ExtractionResult:
#     """
#     Validate and coerce arbitrary parsed JSON into our expected shape.
#     Falls back to empty triplets if shape is wrong.
#     """
#     empty_result: ExtractionResult = {"sentence": sentence, "triplets": []}

#     if not isinstance(obj, dict):
#         return empty_result

#     out_sentence = obj.get("sentence", sentence)
#     triplets = obj.get("triplets", [])

#     # normalize triplets to list[TripletSOP]
#     norm_triplets: list[TripletSOP] = []
#     if isinstance(triplets, list):
#         for item in triplets:
#             # accept list/tuple of len 3
#             if isinstance(item, (list, tuple)) and len(item) == 3:
#                 subject, object, rel = item
#                 if all(isinstance(x, str) for x in (subject, object, rel)):
#                     # enforce (Subject, Object, Relation) order
#                     norm_triplets.append((subject.strip(), object.strip(), rel.strip()))
#             # also accept dicts like {"subject": "...", "object": "...", "relation": "..."}
#             elif isinstance(item, dict):
#                 subject = item.get("subject")
#                 object  = item.get("object")
#                 rel   = item.get("relation")
#                 if all(isinstance(x, str) for x in (subject, object, rel)):
#                     norm_triplets.append((str(subject).strip(), str(object).strip(), str(rel).strip()))

#     return { "sentence": str(out_sentence), "triplets": norm_triplets }


# def coerce_triplets_batch(
#     items: list[dict],
#     original_sentences: list[str]
# ) -> list[ExtractionResult]:
#     """
#     Coerce a parsed JSON array into list[ExtractionResult].

#     items is guaranteed to be a list (via ensure_json_array).
#     """
#     # Prepare fallback empty results
#     fallback: List[ExtractionResult] = [
#         {"sentence": s, "triplets": []}
#         for s in original_sentences
#     ]

#     if not items:
#         return fallback

#     results_by_id: dict[int, ExtractionResult] = {}

#     for item in items:
#         if not isinstance(item, dict):
#             continue
        
#         idx = item.get("id")
#         if not isinstance(idx, int):
#             # Allow "0", "1", etc. but reject others
#             if idx is None:
#                 continue
#             try:
#                 idx = int(idx)
#             except Exception:
#                 continue

#         if not (0 <= idx < len(original_sentences)):
#             continue

#         base_sentence = original_sentences[idx]

#         # Validate structure using the existing logic
#         coerced = coerce_triplets(item, base_sentence)
#         results_by_id[idx] = coerced

#     # Ensure results are in the same order as input sentences
#     ordered_results = [
#         results_by_id.get(i, fallback[i])
#         for i in range(len(original_sentences))
#     ]

#     return ordered_results

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
