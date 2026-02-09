from core.types import ExtractionResult, TripletSubjectObjectPredicate
from typing import Any
import re

# -------------------------
# Robust JSON post-processing helpers
# -------------------------
def _strip_markdown_fences(text: str) -> str:
    # remove ```json ... ``` or ``` ... ```
    return re.sub(r"```(?:json)?\s*|```", "", text, flags=re.IGNORECASE).strip()

def _extract_json_object(text: str) -> str | None:
    """
    Try to locate a top-level JSON object {...} even if the model added extra text.
    Uses a simple brace counter to find the first balanced object.
    """
    s = _strip_markdown_fences(text)
    start = s.find("{")
    if start == -1:
        # no opening brace found
        return None
    depth = 0
    for i, ch in enumerate(s[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start:i+1]
    return None

def _coerce_to_result(obj: Any, sentence: str) -> ExtractionResult:
    """
    Validate and coerce arbitrary parsed JSON into our expected shape.
    Falls back to empty triplets if shape is wrong.
    """
    empty_result: ExtractionResult = {"sentence": sentence, "triplets": []}

    if not isinstance(obj, dict):
        return empty_result

    out_sentence = obj.get("sentence", sentence)
    triplets = obj.get("triplets", [])

    # normalize triplets to list[TripletSubjectObjectPredicate]
    norm_triplets: list[TripletSubjectObjectPredicate] = []
    if isinstance(triplets, list):
        for item in triplets:
            # accept list/tuple of len 3
            if isinstance(item, (list, tuple)) and len(item) == 3:
                subject, object, rel = item
                if all(isinstance(x, str) for x in (subject, object, rel)):
                    # enforce (Subject, Object, Relation) order
                    norm_triplets.append((subject.strip(), object.strip(), rel.strip()))
            # also accept dicts like {"subject": "...", "object": "...", "relation": "..."}
            elif isinstance(item, dict):
                subject = item.get("subject")
                object  = item.get("object")
                rel   = item.get("relation")
                if all(isinstance(x, str) for x in (subject, object, rel)):
                    norm_triplets.append((str(subject).strip(), str(object).strip(), str(rel).strip()))

    return { "sentence": str(out_sentence), "triplets": norm_triplets }
