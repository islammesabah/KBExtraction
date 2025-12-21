from typing import Iterable, List, Sequence
from kbdebugger.llm.hf_backend import use_hf_local, get_hf_causal_model
from kbdebugger.llm.model_access import respond
from kbdebugger.prompts import load_json_resource, render_prompt
from kbdebugger.utils.json import ensure_json_object
from kbdebugger.extraction.utils import coerce_triplets_batch
from kbdebugger.types import ExtractionResult
import json
import torch # type: ignore
import rich

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



def _batched(seq: Sequence[str], batch_size: int) -> Iterable[List[str]]:
    for i in range(0, len(seq), batch_size):
        yield list(seq[i : i + batch_size])

def extract_triplets_batch(
    sentences: Iterable[str],
    *,
    batch_size: int = 5,
) -> List[ExtractionResult]:
    sent_list = [s.strip() for s in sentences if s and s.strip()]
    if not sent_list:
        return []

    all_results: List[ExtractionResult] = []

    for batch in _batched(sent_list, batch_size):
        if use_hf_local():
            batch_results = _extract_batch_via_hf(batch)
        else:
            batch_results = _extract_batch_via_llm(batch)
        all_results.extend(batch_results)

    return all_results

