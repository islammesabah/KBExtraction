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
from .extraction_helpers import _coerce_to_result
from kbdebugger.utils.json import _extract_json_object
from kbdebugger.llm.model_access import get_llm_responder

# -------------------------
# Backend selection helper
# -------------------------
def _use_hf_local() -> bool:
    """
    The key idea: don't import/instantiate large HF models unless the backend is hf_local.
    Returns:
        bool: True if using hf_local backend, False otherwise.
    """
    return os.getenv("MODEL_BACKEND", "hf_local").lower() == "hf_local"

# -------------------------
# HF lazy loader (only if needed)
# -------------------------
_tokenizer = None
_model = None
_DEVICE = "cpu"
_HAVE_BNB = False
_bnb_config = None

def _lazy_load_hf() -> None:
    global _tokenizer, _model, _DEVICE, _HAVE_BNB, _bnb_config
    if _model is not None and _tokenizer is not None:
        return

    # Imports only when actually needed
    from peft import AutoPeftModelForCausalLM
    from transformers import AutoTokenizer, AutoModelForCausalLM

    try:
        from transformers import BitsAndBytesConfig # will fail on Windows/CPU
        _HAVE_BNB = True
    except Exception:
        BitsAndBytesConfig = None  # type: ignore
        _HAVE_BNB = False
        
USE_CUDA = os.getenv("USE_CUDA", "0").strip() == "1"
_DEVICE = "cuda" if USE_CUDA and torch.cuda.is_available() else "cpu"
print(f"[Triplet_Extraction] Running on {_DEVICE.upper()} (USE_CUDA={USE_CUDA})")

LOCAL_PEFT_DIR = os.getenv("PEFT_MODEL_PATH", "Graph_Structuring/fine-tuned-mistral")
HUB_MODEL_ID  = os.getenv("MODEL_ID", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
model_source = LOCAL_PEFT_DIR if os.path.isdir(LOCAL_PEFT_DIR) else HUB_MODEL_ID
print(f"[Triplet_Extraction] Loading model from: {model_source}")

torch_dtype = torch.float16 if _DEVICE == "cuda" else torch.float32
load_kwargs: Dict[str, Any] = {"low_cpu_mem_usage": True, "dtype": torch_dtype}


if _DEVICE == "cuda" and _HAVE_BNB and BitsAndBytesConfig is not None:
    _bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,                      # Q = 4 bits
        #bnb_4bit_use_double_quant=True,        # double quantization, quantizing the quantization constants for saving an additional 0.4 bits per parameter
        bnb_4bit_quant_type="nf4",              # 4-bit NormalFloat Quantization (optimal for normal weights; enforces w ∈ [-1,1])
        bnb_4bit_compute_dtype=torch.bfloat16   # Dequantize to 16-bits before computations (as in the paper)
    )
    load_kwargs["quantization_config"] = _bnb_config
    load_kwargs["device_map"] = "auto"
    print("✅ [Triplet_Extraction] 4-bit quantization enabled")
else:
    print("❌ [Triplet_Extraction] Loading without quantization")
    
def _is_peft_dir(path: str) -> bool:
    return os.path.isdir(path) and os.path.isfile(os.path.join(path, "adapter_config.json"))

if _is_peft_dir(model_source):
    print("[Triplets] Detected PEFT adapter")
    _model_local = AutoPeftModelForCausalLM.from_pretrained(model_source, **load_kwargs)
else:
    _model_local = AutoModelForCausalLM.from_pretrained(model_source, **load_kwargs)

_tokenizer_local = AutoTokenizer.from_pretrained(model_source)
_tokenizer_local.pad_token = _tokenizer_local.eos_token
_tokenizer_local.padding_side = "right"

# Enable attention cache during inference if available
try:
    _model_local.config.use_cache = True
except Exception:
    pass

# Move to device for non-quantized / CPU case
# otherwise, device_map="auto" above handles it.
if _bnb_config is None:
    _model_local.to(_DEVICE) # type: ignore


_model = _model_local
_tokenizer = _tokenizer_local

def build_triplet_extraction_prompt(sentence: str) -> str:
    # Safely JSON-escape the sentence so quotes don't break the prompt
    sent_json = json.dumps(sentence.strip())

    return f"""
You are an information extraction system. Extract relationships (triplets) from a single sentence.

Each relationship MUST be a triplet in the exact order:
(Subject, Object, Relation)

Return STRICT, COMPACT JSON ONLY (no prose, no markdown, no newlines/indentation). Use this schema exactly:
{{"sentence": <string>, "triplets": [[<Subject>, <Object>, <Relation>], ...]}}

Rules:
- Do not invent entities or relationships not present in the sentence.
- Trim whitespace; keep original casing.
- If the sentence is already short enough, don't decompose it further.
- Make sure that the sentence after decomposition still makes sense. If not, keep it as is.
- If no triplets exist, return "triplets": [].


Example:
Input: "Privacy and data governance ensures prevention of harm"
Output: {{"sentence": "Privacy and data governance ensures prevention of harm","triplets": [["Privacy", "harm", "ensures prevention of"],["data governance", "harm", "ensures prevention of"]]}}

Input: "Fairness is a Characteristic of KI system"
Output: {{"sentence": "Fairness is a Characteristic of KI system","triplets": [["Fairness", "KI system", "is a Characteristic of"]]}}
Notice that here we did not decompose further since the sentence is already short.

Now extract for this input:
{sent_json}
""".strip()

# -------------------------
# LLM path (Groq / HTTP / any responder)
# -------------------------
def _extract_via_llm(sentence: str) -> ExtractionResult:
    """
    Given an input sentence, generate triplets using the model.
    Returns an ExtractionResult (sentence + triplets) when possible,
    otherwise a dict with empty triplets.
    """
    empty: ExtractionResult = {"sentence": sentence, "triplets": []}
    prompt = build_triplet_extraction_prompt(sentence)

    llm = get_llm_responder()
    response = llm.invoke({
        "prompt": prompt,
        "max_tokens": 256,
        "temperature": 0.0,
        # If using Groq, this triggers JSON object mode; other backends ignore it.
        "json_mode": True,
    })

    # Optional belt-and-suspenders: strip escaped newlines if any
    response = response.replace("\n", "").replace("\r", "").strip()

    try:
        parsed = json.loads(response)
        return _coerce_to_result(parsed, sentence)
    except Exception:
        pass

    blob = _extract_json_object(response)
    if blob:
        try:
            blob = blob.replace("\n", "").replace("\r", "")
            parsed = json.loads(blob)
            return _coerce_to_result(parsed, sentence)
        except Exception:
            pass

    rich.print("[extract_triplets] ⚠️ Could not parse JSON from LLM; returning empty result.")
    return empty

# -------------------------
# HF path (lazy-loaded local model)
# -------------------------
@torch.no_grad()
def _extract_via_hf(sentence: str) -> ExtractionResult:
    empty: ExtractionResult = {"sentence": sentence, "triplets": []}
    try:
        _lazy_load_hf()
        if _tokenizer is None or _model is None:
            rich.print("[extract_triplets] ❌ Model or tokenizer not loaded; returning empty result.")
            return empty
        prompt = build_triplet_extraction_prompt(sentence)
        inputs = _tokenizer(
            prompt, 
            return_tensors='pt', 
            padding=True
        )
        inputs = {k: v.to(_DEVICE) for k, v in inputs.items()}
        output_tokens = _model.generate(
            inputs["input_ids"],
            attention_mask=inputs.get("attention_mask", None),
            pad_token_id=_tokenizer.pad_token_id,
            max_new_tokens=128,
        )[0]
        res_text = _tokenizer.decode(output_tokens, skip_special_tokens=True)
        # remove prompt echo if present
        res_text = res_text.replace(prompt, "")
        
        # Since the result should be a dictionary, e.g.,
        # {
        #   'triplets': [ 
        #              ['Privacy', 'harm', 'ensures prevention of'], 
        #              ['data governance', 'harm', 'ensures prevention of']
        #            ], 
        #   'sentence': 'Privacy and data governance ensures prevention of harm'}
        # }
        # Try strict JSON first; if that fails, fallback to a curly-brace slice
        
        try:
            parsed = json.loads(res_text)
            return _coerce_to_result(parsed, sentence)
        except Exception:
            # Try to slice out the first balanced {...}
            blob = _extract_json_object(res_text)
            if blob:
                try:
                    parsed = json.loads(blob)
                    return _coerce_to_result(parsed, sentence)
                except Exception:
                    pass

        rich.print("[extract_triplets] ⚠️ Could not parse JSON; returning empty result.")
        return empty
    
    except Exception as e:
        rich.print(f"[extract_triplets] ❌ Exception: {e}")
        return empty

# -------------------------
# Public API
# -------------------------
def extract_triplets(sentence: str) -> ExtractionResult:
    """
    Choose backend by MODEL_BACKEND. If 'hf_local', run HF; otherwise use LLMResponder (e.g., Groq).
    """
    if _use_hf_local():
        return _extract_via_hf(sentence)
    return _extract_via_llm(sentence)