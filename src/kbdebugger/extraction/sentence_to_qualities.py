from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, List
import json

from kbdebugger.extraction.types import TextDecomposer, Qualities
from kbdebugger.llm.model_access import respond
from kbdebugger.utils.json import ensure_json_object
from kbdebugger.prompts import render_prompt, load_json_resource
from .utils import coerce_qualities

@dataclass(frozen=True)
class DecomposeConfig:
    prompt_max_newlines: int = 2

def build_sentence_decomposer(config: DecomposeConfig | None = None) -> TextDecomposer:
    cfg = config or DecomposeConfig()

    # load examples once from JSON
    examples = load_json_resource("sentence_decompose")
    examples_json = json.dumps(examples, ensure_ascii=False)

    def decompose_sentence(sentence: str) -> Qualities:
        # 1. Light sanitization: collapse all whitespace, keep full content
        # i.e., newlines/tabs → spaces, multiple spaces → single space
        s = re.sub(r"\s+", " ", sentence).strip()
        if not s:
            return []

        sentence_json = json.dumps(s, ensure_ascii=False)

        # 2. build prompt from template + json examples
        prompt_str = render_prompt(
            "sentence_decompose",
            examples_json=examples_json,
            sentence_json=sentence_json,
        )

        # 3. call LLM
        response = respond(
            prompt_str,
            max_tokens=2048,
            temperature=0.0,
            json_mode=True,
        )

        # 4. parse JSON
        obj = ensure_json_object(response)
        qualities = coerce_qualities(obj)
        if qualities:
            return qualities

        # 5. weak fallback: split plain text lines
        fallback = [
            line.strip("-• ").strip() # Why -• ? Some models use these as bullet points.
            for line in response.splitlines()
            if line.strip()
        ]
        return fallback if fallback else []

    return decompose_sentence
