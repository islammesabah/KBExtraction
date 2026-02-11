import math
import os
from typing import Iterable, List, Sequence
from kbdebugger.llm.hf_backend import use_hf_local, get_hf_causal_model
from kbdebugger.llm.model_access import respond
from kbdebugger.novelty.types import QualityNoveltyResult
from kbdebugger.prompts import load_json_resource, render_prompt
from kbdebugger.utils.json import ensure_json_object
from kbdebugger.types import ExtractionResult
from kbdebugger.utils import batched
from kbdebugger.extraction.utils import (
    coerce_triplets_batch, 
    save_results_json,
    load_triplet_qualifying_decisions,
)
import json
from kbdebugger.vector.types import KeptQuality
import torch # type: ignore
import rich
from rich.progress import track

def build_triplet_extraction_prompt_batch(sentences: list[str]) -> str:
    """
    Build a prompt that asks the LLM to extract triplets for multiple sentences
    in one call, returning a single JSON object:

    {
      "triplets_batch": [
        {"id": 0, "sentence": "...", "triplets": [...]},
        ...
      ]
    }
    """
    # Load few-shot examples once from JSON
    examples = load_json_resource("triplets_batch")
    examples_json = json.dumps(examples, ensure_ascii=False)
    
    payload = [
        {"id": i, "sentence": s.strip()}
        for i, s in enumerate(sentences)
        if s.strip()
    ]
    payload_json = json.dumps(payload, ensure_ascii=False)
    
    
    return render_prompt(
        "triplets_batch", 
        examples_json=examples_json,
        payload_json=payload_json
    )


def _extract_batch_via_llm(sentences: list[str]) -> list[ExtractionResult]:
    if not sentences:
        return []

    prompt = build_triplet_extraction_prompt_batch(sentences)
    response = respond(
        prompt,
        max_tokens=4096,
        temperature=0.0,
        json_mode=True
    )

    parsed = ensure_json_object(response)
    triplets = coerce_triplets_batch(parsed, sentences)

    return triplets


@torch.no_grad()
def _extract_batch_via_hf(sentences: list[str]) -> list[ExtractionResult]:
    if not sentences:
        return []

    try:
        model, tokenizer, device = get_hf_causal_model()
    except Exception as e:
        rich.print(f"[extract_triplets_batch] ❌ Could not load HF model: {e}")
        return [{"sentence": s, "triplets": []} for s in sentences]

    prompt = build_triplet_extraction_prompt_batch(sentences)
    inputs = tokenizer(prompt, return_tensors="pt", padding=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    output_tokens = model.generate(
        inputs["input_ids"],
        attention_mask=inputs.get("attention_mask"),
        pad_token_id=tokenizer.pad_token_id,
        max_new_tokens=512,
    )[0]

    res_text = tokenizer.decode(output_tokens, skip_special_tokens=True)
    res_text = res_text.replace(prompt, "")

    parsed = ensure_json_object(res_text)
    return coerce_triplets_batch(parsed, sentences)


def extract_triplets_batch(
    sentences: Iterable[str],
    *,
    batch_size: int = 5,
) -> List[ExtractionResult]:
    sent_list = [s.strip() for s in sentences if s and s.strip()]
    if not sent_list:
        return []

    all_results: List[ExtractionResult] = []

    num_batches = math.ceil(len(sent_list) / batch_size) # No iterator materialization

    for batch in track(
        batched(sent_list, batch_size),
        description=f"🧬 Triplet extraction: sentences → S-P-O. (batch size={batch_size}, num_batches={num_batches})",
        total=num_batches,
    ):
        if use_hf_local():
            batch_results = _extract_batch_via_hf(batch)
        else:
            batch_results = _extract_batch_via_llm(batch)
        all_results.extend(batch_results)

    save_results_json(all_results)
    
    return all_results


def extract_triplets_from_novelty_results(
    results: Sequence[QualityNoveltyResult],
    *,
    batch_size: int = 5,
) -> List[ExtractionResult]:
    """
    Extract KG triplets from novelty results based on decision policy.

    This function:
    1) Reads KB_TRIPLET_QUALIFY_DECISIONS from env
    2) Filters QualityNoveltyResult by decision
    3) Extracts the corresponding quality sentences
    4) Calls extract_triplets_batch on them

    Args:
        results:
            Novelty comparator results.
        batch_size:
            Batch size for LLM triplet extraction.

    Returns:
        List of ExtractionResult.
    """
    # qualifying_decisions = load_triplet_qualifying_decisions()

    sentences: List[str] = [
        r.quality
        for r in results
        # if r.decision in qualifying_decisions
    ]

    if not sentences:
        return []

    return extract_triplets_batch(
        sentences,
        batch_size=batch_size,
    )


def extract_triplets_from_kept_qualities(
    kept_qualities: Sequence[KeptQuality],
    *,
    batch_size: int = 5,
) -> List[ExtractionResult]:

    sentences: List[str] = [
        q["quality"]
        for q in kept_qualities
    ]

    if not sentences:
        return []
    
    return extract_triplets_batch(
        sentences,
        batch_size=batch_size,
    )
