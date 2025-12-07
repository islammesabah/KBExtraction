from __future__ import annotations
from dotenv import load_dotenv

from dataclasses import dataclass
from typing import Any, NoReturn, Final
import os
import time

import requests
from .groq_responder import GroqResponder
from .llm_protocol import LLMResponder

# -----------------------------
# Public protocol (matches your code)
# -----------------------------
# class LLMResponder(Protocol):
#     """
#     Minimal interface expected by the rest of the codebase.
#     Convention here: inputs MUST contain a "prompt" key with a string.
#     """
#     def invoke(self, inputs: dict[str, Any]) -> str: ...
#     # def invoke(self, prompt: str) -> str: ...


# -----------------------------
# Environment / config
# -----------------------------
load_dotenv(override=True)

# Select backend: "http" (default) or "hf_local"
MODEL_BACKEND: Final[str] = os.getenv("MODEL_BACKEND", "http").lower()

# HTTP backend config (OpenAI/compatible chat completions)
MODEL_SERVICE_URL: Final[str] = os.getenv(
    "MODEL_SERVICE_URL",
    "http://serv-3306.kl.dfki.de:8000/v1/chat/completions",
)

MODEL_SERVICE_NAME: Final[str] = os.getenv(
    "MODEL_SERVICE_NAME",
    "llama3.3-70b-instruct-fp8",
)

REQUEST_TIMEOUT: Final[float] = float(os.getenv("REQUEST_TIMEOUT", "30.0")) # seconds
REQUEST_RETRIES: Final[int] = int(os.getenv("REQUEST_RETRIES", "2"))

# HF local fallback model (CPU-friendly)
HF_LOCAL_MODEL: Final[str] = os.getenv(
    "HF_LOCAL_MODEL",
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
)
HF_DEVICE: Final[str] = os.getenv("HF_DEVICE", "cpu")  # e.g., "cpu" or "cuda"
HF_MAX_NEW_TOKENS: Final[int] = int(os.getenv("HF_MAX_NEW_TOKENS", "256"))


# -----------------------------
# HTTP (OpenAI-compatible) client
# -----------------------------
@dataclass
class HTTPChatResponder:
    """
    Calls an OpenAI-compatible /v1/chat/completions endpoint.

    Expected inputs to .invoke():
    {
        "prompt": "<final prompt string>",   # required
        "max_tokens": 500,                   # optional override
        "temperature": 0.2,                  # optional
        ...
    }

    Returns assistant message content as a string.
    """
    url: str
    model: str
    timeout: float = 30.0
    retries: int = 2

    def invoke(self, inputs: dict[str, Any]) -> str:
        prompt = inputs.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("HTTPChatResponder.invoke expects inputs['prompt'] as a non-empty string.")

        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": int(inputs.get("max_tokens", 500)),
        }
        if "temperature" in inputs:
            data["temperature"] = float(inputs["temperature"])

        last_exception: Exception | None = None
        for attempt in range(1, self.retries + 2):  # first try + retries
            try:
                resp = requests.post(self.url, json=data, timeout=self.timeout)
                resp.raise_for_status() # Raises HTTPError, if one occurred.
                payload = resp.json()
                # Expect OpenAI-like shape
                content = payload["choices"][0]["message"]["content"]
                return content
            except Exception as exc:
                last_exception = exc
                if attempt <= self.retries:
                    time.sleep(0.5 * attempt)
                    continue
                else:
                    raise RuntimeError(f"HTTPChatResponder failed after {attempt} attempts: {exc}") from exc
                
        # It should not reach here, but mypy needs a return
        return ""
        
        # # This should never be reached due to the raise above, but added for type safety
        # raise RuntimeError(f"HTTPChatResponder failed after all attempts: {last_exception}")


# -----------------------------
# HF local client (simple text-generation)
# -----------------------------
class HFLocalResponder:
    """
    Minimal local Hugging Face text-generation backend.
    Loads model/tokenizer lazily on first call. Works on 🚗 CPU by default.

    Expected inputs to .invoke():
    {
        "prompt": "<final prompt string>",   # required
        "max_tokens": 256,                   # optional override
        ...
    }

    Returns plain generated text string (no special chat formatting).
    """
    def __init__(self, model_name: str, device: str = "cpu", max_new_tokens: int = 256) -> None:
        self.model_name = model_name
        self.device = device
        self.default_max_new_tokens = max_new_tokens
        self._pipe = None  # lazy init

    def _ensure_pipeline(self):
        if self._pipe is not None:
            return
        # Lazy import to avoid heavy deps until needed
        from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline  # type: ignore
        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModelForCausalLM.from_pretrained(self.model_name)
        self._pipe = pipeline(
            task="text-generation",
            model=model,
            tokenizer=tokenizer,
            device=0 if self.device == "cuda" else -1,
        )

    def invoke(self, inputs: dict[str, Any]) -> str:
        prompt = inputs.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("HFLocalResponder.invoke expects inputs['prompt'] as a non-empty string.")
        max_new_tokens = int(inputs.get("max_tokens", self.default_max_new_tokens))
        self._ensure_pipeline()

        # Generate; pipeline returns list[dict]
        outs = self._pipe(prompt, max_new_tokens=max_new_tokens)  # type: ignore[attr-defined]
        if isinstance(outs, list) and outs and "generated_text" in outs[0]:
            return outs[0]["generated_text"]
        # Fallback stringify
        return str(outs)


def _unsupported_backend(backend: str) -> NoReturn:
    raise ValueError(f"Unsupported MODEL_BACKEND: {backend!r}")

# -----------------------------
# Factory
# -----------------------------
def get_llm_responder() -> LLMResponder:
    """
    Factory that returns an object satisfying LLMResponder.
    Chooses backend via MODEL_BACKEND: "groq", "http", or "hf_local".

    Usage:
        llm = get_llm_responder()
        result = llm.invoke({"prompt": "Hello model!"})
    """
    backend = os.getenv("MODEL_BACKEND", "groq").lower()

    match backend:
        case "groq":
            return GroqResponder(model=os.getenv("GROQ_MODEL"))
        case "hf_local":
            return HFLocalResponder(
                model_name=HF_LOCAL_MODEL,
                device=HF_DEVICE,
                max_new_tokens=HF_MAX_NEW_TOKENS,
            )
        case "http":
            return HTTPChatResponder(
                url=MODEL_SERVICE_URL,
                model=MODEL_SERVICE_NAME,
                timeout=REQUEST_TIMEOUT,
                retries=REQUEST_RETRIES,
            )
        case _:
            _unsupported_backend(backend)  # NoReturn → type checker knows we never return here


# -----------------------------
# Convenience wrapper (optional)
# -----------------------------
def respond(prompt: str, **kwargs: Any) -> str:
    """
    Convenience function for one-off calls without importing the responder:
        respond("your final prompt string", max_tokens=200)

    Equivalent to:
        get_llm_responder().invoke({"prompt": prompt, "max_tokens": 200})
    """
    llm = get_llm_responder()
    payload: dict[str, Any] = {"prompt": prompt}
    payload.update(kwargs)
    response = llm.invoke(payload)
    return response
