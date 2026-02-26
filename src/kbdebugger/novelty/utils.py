from __future__ import annotations

import rich

from typing import Any, Dict, Mapping, Mapping, Sequence, cast, List
from dataclasses import asdict

from kbdebugger.subgraph_similarity.types import KeptQuality, NeighborHit

from .types import (
    NoveltyDecision,
    NeighborView,
    QualityNoveltyResult,
    QualityNoveltyResultRaw,
    QualityNoveltyInput,
)


def neighbor_hit_to_view(hit: NeighborHit) -> NeighborView | None:
    """
    Convert a rich NeighborHit into a slim NeighborView.

    Returns None if the KG sentence cannot be extracted.
    """
    relation = hit.get("relation")
    if not isinstance(relation, dict):
        return None

    edge = relation.get("edge")
    if not isinstance(edge, dict):
        return None

    props = edge.get("properties")
    if not isinstance(props, dict):
        return None

    sentence = props.get("sentence")
    if not isinstance(sentence, str) or not sentence.strip():
        return None

    score = float(hit.get("score", 0.0))
    return NeighborView(score=score, sentence=sentence.strip())


def kept_quality_to_novelty_input(
    kept: KeptQuality,
    *,
    top_k: int = 3,
) -> QualityNoveltyInput:
    """
    Convert SubgraphSimilarityFilter output (KeptQuality) into Novelty stage input
    (QualityNoveltyInput) with slim neighbors.

    Args:
        kept: KeptQuality from vector filter.
        top_k: How many neighbors to keep (default 3).

    Returns:
        QualityNoveltyInput ready to be fed to the novelty comparator.
    """
    quality = str(kept["quality"]).strip()
    max_score = float(kept["max_score"])

    views: List[NeighborView] = []
    for hit in kept["neighbors"][: max(1, top_k)]:
        view = neighbor_hit_to_view(hit)
        if view is not None:
            views.append(view)

    return QualityNoveltyInput(quality=quality, neighbors=views, max_score=max_score)


def _coerce_float_0_1(value: Any, *, field: str) -> float:
    """Parse float and validate [0,1]."""
    try:
        f = float(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Field '{field}' must be a number, got: {value!r}") from e
    if not (0.0 <= f <= 1.0):
        raise ValueError(f"Field '{field}' must be within [0,1], got: {f}")
    return f


def coerce_quality_novelty_result(
        parsed: Mapping[str, Any],
        *,
        novelty_input: QualityNoveltyInput,
    ) -> QualityNoveltyResult:
    """
    Coerce parsed model JSON into a typed QualityNoveltyResult, enriched with
    the original quality + max_score from novelty_input.

    This function is intentionally forgiving:
    - If fields are missing, it falls back to safe defaults.
    - If decision is invalid, it defaults to PARTIALLY_NEW (safe behavior: keep signal).
    - Ensures confidence is in [0,1].
    """
    obj = cast(QualityNoveltyResultRaw, dict(parsed))

    decision_raw = str(obj.get("decision", "")).strip().upper()
    if decision_raw not in {d.value for d in NoveltyDecision}:
        rich.print(
            f"[coerce_quality_novelty_result] ⚠️ Invalid decision '{decision_raw}', defaulting to PARTIALLY_NEW."
        )
        # Safe default: treat as PARTIALLY_NEW to avoid dropping potential signal.
        decision = NoveltyDecision.PARTIALLY_NEW
    else:
        decision = NoveltyDecision(decision_raw)

    rationale = str(parsed.get("rationale", "No rationale provided.")).strip()

    novel_spans = obj.get("novel_spans")
    if not isinstance(novel_spans, list):
        novel_spans = []
    novel_spans = [str(s).strip() for s in novel_spans if str(s).strip()]

    matched = obj.get("matched_neighbor_sentence", None)
    if matched is not None and str(matched).strip():
        matched = str(matched).strip()
    else:
        matched = None

    confidence = _coerce_float_0_1(obj.get("confidence"), field="confidence")

    # Small consistency guard:
    # EXISTING should not claim novel spans; if it does, downgrade to PARTIALLY_NEW.
    if decision == NoveltyDecision.EXISTING and novel_spans:
        rich.print(
            "[coerce_quality_novelty_result] ⚠️ EXISTING result has novel_spans; downgrading to PARTIALLY_NEW."
        )
        decision = NoveltyDecision.PARTIALLY_NEW

    return QualityNoveltyResult(
        quality=novelty_input.quality,
        max_score=novelty_input.max_score,

        decision=decision,
        rationale=rationale,
        novel_spans=novel_spans,
        matched_neighbor_sentence=matched,
        confidence=confidence,
    )


# ============================
# Batching utilities
# ============================
def kept_batch_to_prompt_items(
        batch: Sequence[KeptQuality], 
        *, 
        id_offset: int
    ) -> List[Dict[str, Any]]:
    """
    Convert a batch of KeptQuality objects into the prompt JSON schema for the batched comparator.

    Parameters
    ----------
    batch:
        Batch of kept qualities.

    id_offset:
        Integer offset added to each item's index to create stable ids across batches.

    Returns
    -------
    list[dict[str, Any]]
        Items compatible with the batched prompt contract.

    Notes
    -----
    We use explicit integer ids to enforce alignment between:
    - input items (kept qualities)
    - output results produced by the LLM

    This is crucial: batched calls must be order-robust.
    """
    items: List[Dict[str, Any]] = []
    for i, kept in enumerate(batch):
        novelty_input = kept_quality_to_novelty_input(kept)
        d = asdict(novelty_input)
        d["id"] = id_offset + i
        items.append(d)
    return items


def _extract_batched_results_by_id(parsed: Mapping[str, Any]) -> Dict[int, Mapping[str, Any]]:
    """
    Extract the batched novelty results into an id -> payload mapping.

    Expected input format
    ---------------------
    parsed = {
      "results": [
        {"id": 1, "decision": "...", "rationale": "...", ...},
        {"id": 2, "decision": "...", "rationale": "...", ...},
        ...
      ]
    }

    Expected output format
    ----------------------
    {
        1: {"decision": "...", "rationale": "...", ...},  # payload for item with id 1
        2: {"decision": "...", "rationale": "...", ...},  # payload for item with id 2
        ...
    }

    Returns
    -------
    dict[int, Mapping[str, Any]]
        Mapping from item id -> novelty payload dict.

    Raises
    ------
    ValueError
        If the response structure is invalid (missing results array, wrong types).
    """
    results_raw = parsed.get("results")
    if not isinstance(results_raw, list):
        raise ValueError("Batched novelty response missing 'results' array.")

    id_to_response: Dict[int, Mapping[str, Any]] = {}

    for entry in results_raw:
        if not isinstance(entry, dict):
            continue

        rid = entry.get("id")

        if not isinstance(rid, int):
            continue
        
        # payload is the entry itself minus "id"
        payload = dict(entry)
        payload.pop("id", None)

        id_to_response[rid] = payload

    return id_to_response


def coerce_batched_novelty_response(
    parsed: Mapping[str, Any],
    *,
    id_to_input: Mapping[int, QualityNoveltyInput],
) -> List[QualityNoveltyResult]:
    """
    Parse + validate batched LLM response and coerce into typed results.

    This function enforces alignment between:
    - the ids we sent in the prompt
    - the ids the model returned

    Then it reuses the single-item coercion routine for each payload.

    Parameters
    ----------
    parsed:
        JSON object produced by ensure_json_object(...).

    id_to_input:
        Mapping from item id -> original typed novelty input.
        
        1. We need this to enrich the result with the original `quality` text and `max_score`,
        since the LLM response doesn't have to include those (and often shouldn't, to save tokens and reduce error surface).

        2. Also we use to validate that the LLM returned results for all expected ids and no unexpected ids.

    Returns
    -------
    list[QualityNoveltyResult]
        Results aligned by ascending id order (stable and deterministic).

    Raises
    ------
    ValueError
        If the model output is missing ids or contains unexpected ids.
    """
    id_to_response = _extract_batched_results_by_id(parsed)

    expected_ids = set(id_to_input.keys()) # ids that we sent to the LLM prompt
    received_ids = set(id_to_response.keys()) # ids that the LLM returned in its response

    missing = sorted(expected_ids - received_ids)
    extra = sorted(received_ids - expected_ids)

    if missing or extra:
        raise ValueError(
            "Batched novelty response id mismatch.\n"
            f"Missing ids: {missing}\n"
            f"Extra ids: {extra}"
        )

    # Single source of truth for decision parsing / defaults / guards:
    out: List[QualityNoveltyResult] = []
    for rid in sorted(expected_ids):
        novelty_input = id_to_input[rid]
        payload = id_to_response[rid]
        out.append(
            coerce_quality_novelty_result(payload, novelty_input=novelty_input)
        )

    return out

# For UI routes, we can reuse the same coercion logic to convert browser-sent novelty results
def coerce_from_browser_dict(d: Dict[str, Any]) -> QualityNoveltyResult:
    """
    Convert a browser-sent novelty result dict back into a fully typed
    QualityNoveltyResult using the shared coercion utility.

    This ensures:
    - decision validation
    - safe defaults
    - confidence clamping
    - EXISTING + novel_spans consistency guard
    - zero duplication of logic

    The browser sends enriched results (quality + max_score included),
    so we reconstruct a minimal QualityNoveltyInput and reuse the
    shared coerce_quality_novelty_result().
    """

    quality = str(d.get("quality") or "").strip()
    if not quality:
        raise ValueError("Missing/empty field: quality")

    max_score = float(d.get("max_score", 0.0))

    novelty_input = QualityNoveltyInput(
        quality=quality,
        max_score=max_score,
        # if your QualityNoveltyInput has additional fields,
        # fill with safe defaults here
    )

    return coerce_quality_novelty_result(
        parsed=d,
        novelty_input=novelty_input,
    )