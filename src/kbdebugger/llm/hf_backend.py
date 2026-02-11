from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Tuple

import torch # type: ignore
import rich

from transformers import AutoModelForCausalLM, AutoTokenizer
try:
    from transformers import BitsAndBytesConfig  # type: ignore
except Exception:  # BitsAndBytes not available (e.g., CPU-only install)
    BitsAndBytesConfig = None  # type: ignore

from transformers import PreTrainedModel, PreTrainedTokenizerBase

@dataclass(frozen=True)
class HFBackendConfig:
    """
    Configuration for the local HF backend.

    Values are mostly taken from environment variables so that they can be
    overridden without touching code.
    """
    model_backend: str = os.getenv("MODEL_BACKEND", "hf_local")
    use_cuda_flag: str = os.getenv("USE_CUDA", "0")
    local_peft_dir: str = os.getenv("PEFT_MODEL_PATH", "Graph_Structuring/fine-tuned-mistral")
    hub_model_id: str = os.getenv("MODEL_ID", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")

    @property
    def use_hf_local(self) -> bool:
        return self.model_backend.lower() == "hf_local"

    @property
    def use_cuda(self) -> bool:
        return self.use_cuda_flag.strip() == "1"

    @property
    def device(self) -> str:
        if self.use_cuda and torch.cuda.is_available():
            return "cuda"
        return "cpu"

    @property
    def torch_dtype(self):
        return torch.float16 if self.device == "cuda" else torch.float32

    @property
    def model_source(self) -> str:
        # prefer local PEFT dir if it exists, otherwise hub model id
        if os.path.isdir(self.local_peft_dir):
            return self.local_peft_dir
        return self.hub_model_id

def use_hf_local(config: HFBackendConfig | None = None) -> bool:
    """
    Decide whether to use the HF local backend.
    """
    if config is None:
        config = HFBackendConfig()
    return config.use_hf_local


@lru_cache(maxsize=1)
def get_hf_causal_model(
    config: HFBackendConfig | None = None,
) -> Tuple[PreTrainedModel, PreTrainedTokenizerBase, str]:
    """
    Lazily load a causal LM + tokenizer for local inference.

    Returns:
        (model, tokenizer, device_str)
    """
    if config is None:
        config = HFBackendConfig()

    device = config.device
    rich.print(f"[HFBackend] Running on [bold]{device.upper()}[/bold] (USE_CUDA={config.use_cuda})")

    model_source = config.model_source
    rich.print(f"[HFBackend] Loading model from: [cyan]{model_source}[/cyan]")

    load_kwargs: dict[str, Any] = {
        "low_cpu_mem_usage": True,
        "dtype": config.torch_dtype,
    }

    # ------------------ Optional 4-bit quantization ------------------
    bnb_config = None
    if device == "cuda" and BitsAndBytesConfig is not None:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        load_kwargs["quantization_config"] = bnb_config
        load_kwargs["device_map"] = "auto"
        rich.print("[HFBackend] ✅ 4-bit quantization enabled")
    else:
        rich.print("[HFBackend] ❌ Loading without quantization")

    # ------------------ PEFT vs plain model ------------------
    def _is_peft_dir(path: str) -> bool:
        return os.path.isdir(path) and os.path.isfile(os.path.join(path, "adapter_config.json"))

    if _is_peft_dir(model_source):
        from peft import AutoPeftModelForCausalLM
        rich.print("[HFBackend] Detected PEFT adapter")
        model: PreTrainedModel = AutoPeftModelForCausalLM.from_pretrained(
            model_source,
            **load_kwargs,
        )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            model_source,
            **load_kwargs,
        )

    tokenizer: PreTrainedTokenizerBase = AutoTokenizer.from_pretrained(model_source)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    try:
        model.config.use_cache = True  # type: ignore[attr-defined]
    except Exception:
        pass

    # If we didn't use device_map="auto", move model to device
    if bnb_config is None:
        model.to(device)  # type: ignore[call-arg]

    return model, tokenizer, device