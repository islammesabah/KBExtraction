from __future__ import annotations

import os
from typing import Any, Dict, Optional
from groq import Groq, BadRequestError
from kbdebugger.utils.json import _ensure_json_object

class GroqResponder:
    """
    LLMResponder that calls Groq Chat Completions.
    Expects `inputs` dict with at least {"prompt": "..."}.
    Optional keys: max_tokens (int), temperature (float), json_mode (bool)
    """
    def __init__(self, model: Optional[str] = None) -> None:
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def invoke(self, inputs: Dict[str, Any]) -> str:
        prompt: str = inputs.get("prompt", "")
        
        if not prompt:
            # For JSON mode, empty prompt => empty object
            return "{}" if inputs.get("json_mode", False) else ""

        max_tokens: int = int(inputs.get("max_tokens", 1000))
        temperature: float = float(inputs.get("temperature", 0.0))
        json_mode: bool = bool(inputs.get("json_mode", True))  # default: Respond with JSON

        # System prompts
        if json_mode:
            system_msg = (
                "You are a JSON-only API. "
                "Respond with a single JSON object and nothing else. "
                "Do not include markdown, comments, or explanations. "
                "The response MUST start with '{' and end with '}'."
            )
        else:
            system_msg = "Be helpful."

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ]

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": max_tokens,
            "temperature": temperature,
        }

        # Strategy:
        # 1) Try strict Groq JSON mode (if json_mode=True).
        # 2) If Groq returns 400 (json_validate_failed), retry without response_format.
        # 3) Always run _ensure_json_object() on the final content in JSON mode.
        if json_mode:
            # Valid-JSON guarantee (no extra prose)
            kwargs["response_format"] = {"type": "json_object"}

        try:
            resp = self.client.chat.completions.create(**kwargs)
        except BadRequestError as e:
            # Only handle the JSON validate failure specially in JSON mode
            if not json_mode:
                raise

            # Retry WITHOUT response_format, then we'll do our own post-processing
            retry_kwargs = dict(kwargs)
            retry_kwargs.pop("response_format", None)
            resp = self.client.chat.completions.create(**retry_kwargs)

        content = (resp.choices[0].message.content or "").strip()

        if json_mode:
            return _ensure_json_object(content)
        else:
            return content

