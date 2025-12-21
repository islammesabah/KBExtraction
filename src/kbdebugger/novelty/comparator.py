"""
Novelty comparator for extracted "quality" sentences.

This module defines:
- Typed input structures for a candidate quality and its top-k KG neighbors
- A strict JSON output schema for the comparator LLM

This module integrates with the project's existing infrastructure:
- kbdebugger.llm.llm_protocol.LLMResponder
- kbdebugger.prompts.render_prompt + examples loaded from kbdebugger.prompts.examples

The comparator decides whether a candidate quality is:
- EXISTING: no meaningful new semantic value compared to its neighbors
- PARTIALLY_NEW: overlaps strongly but adds meaningful details
- NEW: introduces a new claim/aspect not covered by neighbors
"""

from __future__ import annotations

from dataclasses import asdict

import json
from typing import List, Sequence

from kbdebugger.llm.model_access import respond
from kbdebugger.prompts import load_json_resource, render_prompt
from kbdebugger.vector.types import KeptQuality
from .types import (
    QualityNoveltyResult,
    QualityNoveltyInput,
)
from kbdebugger.utils.json import ensure_json_object
from .utils import (
    coerce_quality_novelty_result, 
    kept_quality_to_novelty_input, 
    save_novelty_results_json,
    pretty_print_novelty_results
)


def build_quality_novelty_prompt(item: QualityNoveltyInput) -> str:
    """
    Build the comparator prompt by injecting:
    - examples_json: few-shot examples loaded from prompts/examples
    - input_json: the current item serialized as JSON

    Args:
        item: quality + neighbors

    Returns:
        Rendered prompt string.
    """
    examples = load_json_resource("quality_novelty_comparator")
    examples_json = json.dumps(examples, ensure_ascii=False)
    
    # Convert dataclass -> JSON (typed object, no ad-hoc dicts)
    input_json = json.dumps(asdict(item), ensure_ascii=False)

    return render_prompt(
        "quality_novelty_comparator",
        examples_json=examples_json,
        input_json=input_json,
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
    End-to-end novelty classification:
      - builds the prompt
      - calls the LLM via respond()
      - parses with ensure_json_object()
      - coerces to NoveltyResult

    Args:
        item: KeptQuality produced by VectorSimilarityFilter.
        max_tokens: LLM generation budget.
        temperature: decoding temperature.

    Returns:
        QualityNoveltyResult instance.
    """
    novelty_input = kept_quality_to_novelty_input(kept)
    prompt = build_quality_novelty_prompt(novelty_input)
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
    max_tokens: int = 700,
    temperature: float = 0.0,
) -> List[QualityNoveltyResult]:
    """
    Convenience helper: classify an entire list of kept qualities.

    This is intentionally sequential (one LLM call per kept item) because the
    decision depends on each item's unique neighbors.

    Returns:
        List of NoveltyResult aligned with `kept` order.
    """
    results: List[QualityNoveltyResult] = []
    
    for kept_quality in kept_qualities:
        result = classify_quality_novelty(kept_quality, max_tokens=max_tokens, temperature=temperature)
        results.append(result)

    pretty_print_novelty_results(kept=kept_qualities, results=results)
    
    save_novelty_results_json(results)
    
    return results
