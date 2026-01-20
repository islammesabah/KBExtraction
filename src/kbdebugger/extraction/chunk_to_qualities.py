from __future__ import annotations

from dataclasses import dataclass
import json
import re

from kbdebugger.extraction.types import TextDecomposer, Qualities
from kbdebugger.llm.model_access import respond
from kbdebugger.utils import ensure_json_object
from kbdebugger.prompts import render_prompt, load_json_resource
from .utils import coerce_qualities


@dataclass(frozen=True)
class ChunkDecomposeConfig:
    # chunks can be longer, so allow more newlines than for single sentences
    prompt_max_newlines: int = 20


def build_chunk_decomposer(
    config: ChunkDecomposeConfig | None = None,
) -> TextDecomposer:
    cfg = config or ChunkDecomposeConfig()

    # Load few-shot examples once from JSON
    examples = load_json_resource("chunk_decompose")
    examples_json = json.dumps(examples, ensure_ascii=False)

    def decompose_chunk(text: str) -> Qualities:
        """
        Extract ordered, atomic 'qualities' from a larger paragraph/chunk.
        Returns a list of short statements.
        """
        # 1. Light sanitization: collapse all whitespace, keep full content
        # i.e., newlines/tabs → spaces, multiple spaces → single space
        s = re.sub(r"\s+", " ", text).strip()
        if not s:
            return []
        
        # We embed the text as a JSON string literal in the prompt
        text_json = json.dumps(s, ensure_ascii=False)

        # 2. Build prompt from template + JSON examples
        prompt_str = render_prompt(
            "chunk_decompose",
            examples_json=examples_json,
            text_json=text_json,
        )

        # 3. Call LLM
        raw_response = respond(
            prompt_str,
            max_tokens=2048,
            temperature=0.0,
            json_mode=True,
        )

        # 4. Parse JSON into Python object
        # qualities = parse_response(response, coercer=coerce_qualities, default=[])
        obj = ensure_json_object(raw_response)
        qualities = coerce_qualities(obj)

        # # 5. Coerce into list[str] (qualities)
        if qualities:
            return qualities


        # 6. Fallback: salvage any plain-text lines from the *raw text*
        fallback = [
            line.strip("-• ").strip()  # strip common bullet prefixes
            for line in str(raw_response).splitlines()
            if line.strip()
        ]
        return fallback if fallback else []
    

    return decompose_chunk
