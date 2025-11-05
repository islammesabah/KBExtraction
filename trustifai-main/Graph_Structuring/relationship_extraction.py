# Safe, device-agnostic loader for PEFT models (CPU by default; CUDA+4bit if available)
# --------------------------------------------------------------------------------------
# For loading a PEFT model, we need to use a special object for CausalLM from PEFT
# instead of the regular HuggingFace object.
from peft import AutoPeftModelForCausalLM
from transformers import AutoTokenizer
from dotenv import load_dotenv
from core.types import ExtractionResult
from .extraction_helpers import _coerce_to_result, _extract_json_object

import torch
import os
import json
import rich

# --- Optional: BitsAndBytes (CUDA-only). Import guarded. ---
try:
    from transformers import BitsAndBytesConfig  # will fail on Windows/CPU
    HAVE_BNB = True
except Exception:
    BitsAndBytesConfig = None  # type: ignore
    HAVE_BNB = False


# -------------------------
# Env & login
# -------------------------
load_dotenv(override=True)

HF_API_TOKEN = os.getenv("HF_API_TOKEN", "").strip()
def maybe_login_hf(repo_or_path: str):
    if HF_API_TOKEN:
        try:
            from huggingface_hub import login
            login(HF_API_TOKEN)
        except Exception:
            pass    # don’t crash if offline; local paths will still work

# Only try to login if a token is present AND we're loading from the Hub
# (local folder paths don't need login)
# def maybe_login_hf(repo_or_path: str):
#     # Only login for remote Hub models (not local directories)
#     if os.path.isdir(repo_or_path):
#         return
#     if "/" in repo_or_path and os.getenv("HF_API_TOKEN", "").strip():
#         try:
#             from huggingface_hub import login
#             login(os.getenv("HF_API_TOKEN").strip())
#         except Exception:
#             pass

# -------------------------
# Device / quantization
# -------------------------
# Detect whether CUDA should be used (default: 0 = off)
USE_CUDA = os.getenv("USE_CUDA", "0").strip() == "1"
DEVICE = "cuda" if USE_CUDA and torch.cuda.is_available() else "cpu"

print(f"[TrustifAI] Running on {DEVICE.upper()} (USE_CUDA={USE_CUDA})")

bnb_config = None
if DEVICE == "cuda" and HAVE_BNB:
    if BitsAndBytesConfig is None:
        raise ImportError("BitsAndBytesConfig is not available, but required for 4-bit quantization.")
    
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,                      # Q = 4 bits
        #bnb_4bit_use_double_quant=True,        # double quantization, quantizing the quantization constants for saving an additional 0.4 bits per parameter
        bnb_4bit_quant_type="nf4",              # 4-bit NormalFloat Quantization (optimal for normal weights; enforces w ∈ [-1,1])
        bnb_4bit_compute_dtype=torch.bfloat16   # Dequantize to 16-bits before computations (as in the paper)
    )


# -------------------------
# Model / tokenizer loading
# -------------------------
# Load the model
# Prefer local PEFT folder if it exists; else use a small public model for CPU
LOCAL_PEFT_DIR = os.getenv("PEFT_MODEL_PATH", "Graph_Structuring/fine-tuned-mistral")
HUB_MODEL_ID  = os.getenv("MODEL_ID", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")  # good CPU test model

def is_peft_dir(path_or_id: str) -> bool:
    """PEFT adapters contain adapter_config.json."""
    # local folder
    if os.path.isdir(path_or_id) and os.path.isfile(os.path.join(path_or_id, "adapter_config.json")):
        return True
    # quick remote heuristic: if it’s a hub id, try to avoid PEFT unless explicitly a PEFT repo
    return False


# peft_model_path = "Graph_Structuring/fine-tuned-mistral"  # local path by default
model_source = LOCAL_PEFT_DIR if os.path.isdir(LOCAL_PEFT_DIR) else HUB_MODEL_ID
print(f"[TrustifAI] Loading model from: {model_source}")
maybe_login_hf(model_source)



# Choose dtype sensibly
torch_dtype = torch.float16 if DEVICE == "cuda" else torch.float32

load_kwargs = {
    "low_cpu_mem_usage": True,
    "dtype": torch_dtype,
}

# Only pass quantization_config if we actually built one
if bnb_config is not None:
    load_kwargs["quantization_config"] = bnb_config
    load_kwargs["device_map"] = "auto"  # let HF place layers on GPU
    print("[TrustifAI] Loading model with 4-bit quantization")
else:
    # load_kwargs["device_map"] = {"": DEVICE}  # empty string means "all layers"
    print("[TrustifAI] Loading model without quantization")


# --- robust loader: use PEFT only if adapter_config.json exists ---
if is_peft_dir(model_source):
    print("[TrustifAI] Detected PEFT adapter; loading with AutoPeftModelForCausalLM")
    model = AutoPeftModelForCausalLM.from_pretrained(model_source, **load_kwargs)
else:
    print("[TrustifAI] No PEFT adapter found; loading base model with AutoModelForCausalLM")
    from transformers import AutoModelForCausalLM
    model = AutoModelForCausalLM.from_pretrained(model_source, **load_kwargs)

# tuned_model = AutoPeftModelForCausalLM.from_pretrained(model_source, **load_kwargs)

# Load the tokenizer
tokenizer = AutoTokenizer.from_pretrained(model_source)

# Set the padding token to be the same as the end-of-sequence token
tokenizer.pad_token = tokenizer.eos_token

# Specify that padding should be added to the right side of the sequences
tokenizer.padding_side = "right"

# Enable attention cache during inference if available
try:
    model.config.use_cache = True
except Exception:
    pass

# Move to device for non-quantized / CPU case
if bnb_config is None:
    model.to(DEVICE)

# -------------------------
# Prompting helpers
# -------------------------
def build_relation_extraction_prompt(sentence: str) -> str:
    """
    Build a STRICT JSON-only instruction for extracting (Subject, Object, Relation) triplets.
    Output schema must be:
    {
      "sentence": "<original sentence>",
      "edges": [["Subject","Object","Relation"], ...]
    }
    """
    # Safely JSON-escape the sentence so quotes don't break the prompt
    sent_json = json.dumps(sentence.strip())

    return f"""
You are an information extraction system. Extract relationships (edges) from a single sentence.

Each relationship MUST be a triplet in the exact order:
(Subject, Object, Relation)

Return STRICT JSON ONLY (no prose, no markdown). Use this schema exactly:
{{
  "sentence": <string>, 
  "edges": [ [<Subject>, <Object>, <Relation>], ... ]
}}

Rules:
- Do not invent entities or relations not present in the sentence.
- Trim whitespace; keep original casing.
- If no edges exist, return "edges": [].

Example:
Input: "Privacy and data governance ensures prevention of harm"
Output:
{{
  "sentence": "Privacy and data governance ensures prevention of harm",
  "edges": [
    ["Privacy", "harm", "ensures prevention of"],
    ["data governance", "harm", "ensures prevention of"]
  ]
}}

Now extract for this input:
{sent_json}
"""

# Define a function to build a prompt from a data example
# def format_instruction(sentence, edges):
#     return f"""
# Extract relationships (edges) from the given sentences. 
# Each relationship should be a triplet in the format `(Subject, Object, Relation)`, where:

# 1. **Subject**: The main entity initiating the action or relationship.
# 2. **Object**: The entity affected by or related to the Subject.
# 3. **Relation**: The action or relationship connecting the Subject and Object.

# Return the results as a list of dictionaries. Each dictionary should have two keys:
# - `"sentence"`: The original sentence.
# - `"edges"`: A list of triplets representing the extracted edges.


# Example:
# Input Sentence: "Privacy and data governance ensures prevention of harm"
# Output: {{'edges': [['Privacy', 'harm', 'ensures prevention of'], ['data governance', 'harm', 'ensures prevention of']], 'sentence': 'Privacy and data governance ensures prevention of harm'}}

# Task:
# Input Sentence: "{sentence.strip()}"
# Output: {edges}
# """

# -------------------------
# Inference
# -------------------------
@torch.no_grad()
def extract_triplets(sentence: str) -> ExtractionResult:
    """
    Given an input sentence, generate edges using the model.
    Returns an ExtractionResult (sentence + edges) when possible,
    otherwise a dict with 'raw' or 'error'.
    """
    empty_result: ExtractionResult = {
        "sentence": sentence, 
        "edges": []
    }
    try:
        prompt = build_relation_extraction_prompt(sentence)
        inputs = tokenizer(prompt, return_tensors='pt', padding=True)
        # inputs = inputs.to("cuda")
        inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
        
        output_tokens = model.generate(
            inputs["input_ids"],
            attention_mask=inputs.get("attention_mask", None),
            pad_token_id=tokenizer.pad_token_id,
            max_new_tokens=128,
        )[0]     # batch of tokens with one sequence
        
        res_text = tokenizer.decode(output_tokens, skip_special_tokens=True)
        res_text = res_text.replace(prompt,"") # so that only the model output remains and not the prompt

        # Since the result should be a dictionary, e.g.,
        # {
        #   'edges': [ 
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
                    pass   # fallthrough to raw

        # 😔 Last resort
        # return { "raw": res_text, "warning": "⚠️ Could not parse JSON; returning raw text." }
        rich.print("[extract_triplets] ⚠️ Could not parse JSON; returning empty result.")
        return empty_result

    except Exception as e:
        rich.print(f"[extract_triplets] ❌ Exception during extraction: {e}")
        # return { "error": str(e), "message": "An error occurred. Please try again." }
        return empty_result
