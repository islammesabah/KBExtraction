from __future__ import annotations

import os
from typing import Any, Dict, Optional
from groq import Groq

class GroqResponder:
    """
    LLMResponder that calls Groq Chat Completions.
    Expects `inputs` dict with at least {"prompt": "..."}.
    Optional keys: max_tokens (int), temperature (float), json_mode (bool)
    """
    def __init__(self,
                 model: Optional[str] = None) -> None:
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def invoke(self, inputs: Dict[str, Any]) -> str:
        prompt: str = inputs.get("prompt", "")
        if not prompt:
            return ""

        max_tokens: int = int(inputs.get("max_tokens", 500))
        temperature: float = float(inputs.get("temperature", 0.0))
        json_mode: bool = bool(inputs.get("json_mode", True))  # default: JSON object mode

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Return a COMPACT JSON object (no indentation, no newlines, no spaces between elements)." if json_mode else "Be helpful."},
                {"role": "user", "content": prompt},
            ],
            "max_completion_tokens": max_tokens,
            "temperature": temperature,
        }

        if json_mode:
            # Valid-JSON guarantee (no extra prose)
            kwargs["response_format"] = {"type": "json_object"}

        resp = self.client.chat.completions.create(**kwargs)
        return (resp.choices[0].message.content or "").strip()

