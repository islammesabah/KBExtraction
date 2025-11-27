from kbdebugger.types import ExtractionResult, TripletSOP
from typing import Any

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

    # normalize triplets to list[TripletSOP]
    norm_triplets: list[TripletSOP] = []
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
