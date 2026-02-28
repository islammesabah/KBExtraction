"""
Novelty comparator for extracted "quality" sentences.

Novelty comparator for extracted "quality" sentences.

This module supports two execution modes:

1) Single-item classification
   - easiest to debug
   - one LLM call per kept quality

2) Batched classification (recommended for throughput)
   - reduces LLM call overhead by grouping items into batches
   - still keeps strict alignment using stable integer ids
   - validates that the model returns exactly one result per input item

The comparator decides whether a candidate quality is:
- EXISTING: no meaningful new semantic value compared to its neighbors
- PARTIALLY_NEW: overlaps strongly but adds meaningful details
- NEW: introduces a new claim/aspect not covered by neighbors
"""

from __future__ import annotations

from dataclasses import asdict

from encodings.punycode import T
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

from kbdebugger.llm.model_access import respond
from kbdebugger.prompts import build_prompt, build_prompt_batch
from kbdebugger.subgraph_similarity.types import KeptQuality
from kbdebugger.types.ui import ProgressCallback
from kbdebugger.utils import batched
from rich.progress import track
from .types import (
    QualityNoveltyResult,
    QualityNoveltyInput,
)
from kbdebugger.utils.json import ensure_json_object
from .utils import (
    coerce_quality_novelty_result, 
    kept_quality_to_novelty_input,
    coerce_batched_novelty_response, 
)
from .logging import (
    save_novelty_results_json,
    pretty_print_novelty_results
)

# -------------------------
# Public API
# -------------------------
def classify_quality_novelty(
    kept: KeptQuality,
    *,
    max_tokens: int = 700,
    temperature: float = 0.0,
) -> QualityNoveltyResult:
    """
    Classify novelty for a single kept quality (one LLM call).

    Kept as a debugging-friendly baseline.

    Parameters
    ----------
    kept:
        A single kept quality with its nearest neighbors.

    max_tokens:
        Maximum generation tokens for the LLM output for this one response.

    temperature:
        Decoding temperature.

    Returns:
    -----------
    QualityNoveltyResult
        Typed novelty decision including decision label, rationale, novel spans, etc.

    """
    # Map KeptQuality to the minimal input schema expected by the prompt.
    novelty_input = kept_quality_to_novelty_input(kept)

    prompt = build_prompt(
        prompt_name="quality_novelty_comparator",
        examples_name="quality_novelty_comparator",
        input_obj=novelty_input,
    )
    response = respond(
        prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        json_mode=True,
    )
    parsed = ensure_json_object(response)
    result = coerce_quality_novelty_result(parsed, novelty_input=novelty_input)
    return result


def classify_qualities_novelty(
    kept_qualities: Sequence[KeptQuality],
    *,
    max_tokens: int = 2048,
    temperature: float = 0.0,
    use_batch: bool = True,
    batch_size: int = 5,
    pretty_print: bool = True,
    progress: Optional[ProgressCallback] = None,
) -> Tuple[
        Sequence[QualityNoveltyResult], 
        Dict
    ]:
    """
    Classify novelty for a list of kept qualities.

    This function supports:
    - sequential mode (use_batch=False): easiest to debug
    - ⚡️ batched mode (use_batch=True): fewer LLM calls, much faster

    Parameters
    ----------
    kept_qualities:
        List of kept qualities (each includes neighbor relations and similarity scores).

    max_tokens:
        Token budget for the LLM output.

        IMPORTANT:
        - In sequential mode, this is "per item".
        - In batched mode, this is "per batch".
        ⚡️ Increase it when you increase `batch_size` or when rationales get long.

    temperature:
        Decoding temperature.

    use_batch:
        If True, run batched LLM calls. If False, run sequential.

    batch_size:
        Number of kept items per LLM call (batched mode only).

    Returns
    -------
    list[QualityNoveltyResult]
        Typed novelty results aligned with the input order.

    Raises
    ------
    ValueError
        If the batched LLM response does not return exactly one result per input id.
    """
    if not kept_qualities:
        return [], {}

    # -------------------------
    # Sequential mode
    # -------------------------
    if not use_batch:
        results: List[QualityNoveltyResult] = []
        for idx, kept in enumerate(kept_qualities, start=1):
            if progress:
                progress(
                    idx,
                    len(kept_qualities),
                    f"🧑🏻‍⚖️ determining novelty for quality",
                )
            results.append(
                classify_quality_novelty(
                    kept,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            )
        pretty_print_novelty_results(kept=kept_qualities, results=results)
        save_novelty_results_json(results)
        return results, {}

    # -------------------------
    # Batched mode
    # -------------------------
    all_results: List[QualityNoveltyResult] = []
    global_id = 0
    num_batches = math.ceil(len(kept_qualities) / batch_size) 

    groups = batched(list(kept_qualities), batch_size=batch_size)

    # Use rich.track only when no UI progress callback is given
    if progress is None:
        groups = track(
            groups,
            description=f"🧑🏻‍⚖️ LLM Novelty Comparator: batch_size={batch_size}, num_batches={num_batches}",
            total=num_batches,
        )


    for batch_idx, group in enumerate(groups, start=1):
        if progress:
            progress(
                batch_idx,
                num_batches,
                f"🧑🏻‍⚖️ determining novelty for a batch of qualities (batch size={len(group)})…",
            )

        # 1) Map each kept quality to the minimal input schema expected by the prompt 
        novelty_inputs: List[QualityNoveltyInput] = [
            kept_quality_to_novelty_input(k) for k in group
        ]

        # 2) 🏗️ Build prompt items with stable integer ids.
        #    We send dicts to the prompt (JSON contract), but we keep the typed
        #    objects (of type: QualityNoveltyInput) separately for coercion and enrichment.
        items_for_prompt: List[Dict[str, Any]] = []
        id_to_input: Dict[int, QualityNoveltyInput] = {}

        for i, ni in enumerate(novelty_inputs):
            rid = global_id + i
            id_to_input[rid] = ni

            # The novelty input dict for the prompt includes all fields of ni + the stable "id" field.
            d = asdict(ni)
            d["id"] = rid
            items_for_prompt.append(d)

        # 3) Build the batched prompt using the shared prompt-builder.
        prompt = build_prompt_batch(
            prompt_name="quality_novelty_comparator_batch",
            examples_name="quality_novelty_comparator",
            items=items_for_prompt,
            # items_var="items_json",
            # wrapper_key="items",
        )

        # 4) Call the LLM once for the entire batch.
        response = respond(prompt, max_tokens=max_tokens, temperature=temperature, json_mode=True)
        parsed = ensure_json_object(response)

        # 5) Parse + validate + coerce using shared coercion logic.
        batch_results = coerce_batched_novelty_response(parsed, id_to_input=id_to_input)
        all_results.extend(batch_results)

        global_id += len(group)

    # all_results is in ascending id order, which matches original kept order.

    if pretty_print:
        pretty_print_novelty_results(kept=kept_qualities, results=all_results)
    
    log_payload = save_novelty_results_json(all_results)
    return all_results, log_payload
