from __future__ import annotations

from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers import BitsAndBytesConfig

# Safe, device-agnostic loader for PEFT models (CPU by default; CUDA+4bit if available)
# --------------------------------------------------------------------------------------
# For loading a PEFT model, we need to use a special object for CausalLM from PEFT
# instead of the regular HuggingFace object.
import os, json, torch, rich
from typing import Dict, Any
from peft import AutoPeftModelForCausalLM
from transformers import AutoTokenizer
from dotenv import load_dotenv
from kbdebugger.types import ExtractionResult
from .utils import coerce_triplets
from kbdebugger.utils.json import ensure_json_object
from kbdebugger.llm.model_access import respond
from kbdebugger.llm.hf_backend import use_hf_local, get_hf_causal_model
from kbdebugger.prompts.prompt_rendering import render_prompt

def build_triplet_extraction_prompt(sentence: str) -> str:
    return render_prompt(
        "triplets_single",
        sentence_json=json.dumps(sentence.strip(), ensure_ascii=False),
    )

# -------------------------
# LLM path (Groq / HTTP / any responder)
# -------------------------
def _extract_via_llm(sentence: str) -> ExtractionResult:
    """
    Given an input sentence, generate triplets using the model.
    Returns an ExtractionResult (sentence + triplets) when possible,
    otherwise a dict with empty triplets.
    """
    # empty: ExtractionResult = {"sentence": sentence, "triplets": []}
    prompt = build_triplet_extraction_prompt(sentence)

    response = respond(prompt, {
        "max_tokens": 512,
        "temperature": 0.0,
        # If using Groq, this triggers JSON object mode; other backends ignore it.
        "json_mode": True,
    })

    # Optional belt-and-suspenders: strip escaped newlines if any
    response = response.replace("\n", "").replace("\r", "").strip()
    obj = ensure_json_object(response)
    return coerce_triplets(obj, sentence)

# -------------------------
# HF path (lazy-loaded local model)
# -------------------------
@torch.no_grad()
def _extract_via_hf(sentence: str) -> ExtractionResult:
    empty: ExtractionResult = {"sentence": sentence, "triplets": []}
    try:
        model, tokenizer, device = get_hf_causal_model()
    except Exception as e:
        rich.print(f"[extract_triplets] ❌ Could not load HF model: {e}")
        return empty

    prompt = build_triplet_extraction_prompt(sentence)
    inputs = tokenizer(prompt, return_tensors="pt", padding=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    output_tokens = model.generate(
        inputs["input_ids"],
        attention_mask=inputs.get("attention_mask"),
        pad_token_id=tokenizer.pad_token_id,
        max_new_tokens=128,
    )[0]

    res_text = tokenizer.decode(output_tokens, skip_special_tokens=True)
    # remove prompt echo if present
    res_text = res_text.replace(prompt, "")

    obj = ensure_json_object(res_text)
    return coerce_triplets(obj, sentence)

# -------------------------
# Public API
# -------------------------
def extract_triplets(sentence: str) -> ExtractionResult:
    """
    Choose backend by MODEL_BACKEND.
    If 'hf_local', run HF; otherwise use remote LLM responder (e.g., Groq).
    """
    if use_hf_local():
        return _extract_via_hf(sentence)
    return _extract_via_llm(sentence)
