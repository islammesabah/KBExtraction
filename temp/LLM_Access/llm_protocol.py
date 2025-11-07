# LLM_Access/llm_protocol.py
from __future__ import annotations
from typing import Protocol, runtime_checkable, Any, Dict

@runtime_checkable
class LLMResponder(Protocol):
    """Minimal interface for an LLM/chain callable."""
    def invoke(self, inputs: Dict[str, Any]) -> str: ...

