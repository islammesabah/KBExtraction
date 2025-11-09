from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Any, Final
import json
from kbdebugger.extraction.types import TextDecomposer, Qualities

from kbdebugger.llm.model_access import respond
from kbdebugger.graph.extraction_helpers import _extract_json_object
 
from kbdebugger.compat.langchain import PromptTemplate
# ---------- Types ----------
class SentenceDecomposeError(RuntimeError):
    """Raised when the LLM response cannot be coerced to the expected schema."""

# class LLMResponder(Protocol):
#     """Minimal interface for an LLM/chain callable (e.g., LangChain Runnable)."""
#     # def invoke(self, inputs: dict[str, Any]) -> str: ...
#     def invoke(self, prompt: str) -> str: ...

@dataclass(frozen=True)
class DecomposeConfig:
    """
    Configuration for sentence decomposition.
    - prompt_max_newlines: cap to avoid pathological inputs.
    """
    prompt_max_newlines: int = 2

# ---------- Prompt Building ----------
_EXAMPLES: Final[list[dict[str, str]]] = [
    {
        "sentence": 'Data Preprocessing is subclass of Data Science Task',
        "output": '["Data Preprocessing is subclass of Data Science Task"]',
    },
    {
        "sentence": (
            'Transparency Property of an →KI system that is explainable and '
            'comprehensible. In the context of this quality standard, "transparency" '
            'also includes documentation of the properties of the →KI system.'
        ),
        "output": '["Transparency is a property of KI system.", '
                  '"Transparency is explainable.", '
                  '"Transparency is comprehensible.", '
                  '"Transparency includes documentation of properties of KI system."]',
    },
    {
        "sentence": (
            "opacity\nopaqueness:\n"
            "Property of a system that appropriate information about the system is "
            "unavailable to relevant stakeholders."
        ),
        "output": '["Opacity also called Opaqueness.", '
                  '"Opacity is a Property of a system.", '
                  '"Property of a system has characteristic Information unavailable to stakeholders."]',
    },
    {
        "sentence": (
            "This requirement is closely linked with the principle of explicability "
            "and encompasses transparency of elements relevant to an AI system: the data, "
            "the system and the business models."
        ),
        "output": '["Requirement is linked with principle of explicability.", '
                  '"Requirement encompasses Transparency of elements.", '
                  '"Transparency is relevant to AI system. 4-Elements include Data.", '
                  '"Elements include System. 6-Elements include Business models."]',
    },
]

_PROMPT_TEMPLATE = """<s>[INST]You are a careful assistant. Extract key, atomic statements ("qualities")
from the given sentence so they form a coherent knowledge graph when read together.

Return STRICT JSON ONLY with this schema:
{{"qualities": ["...", "..."]}}

Rules:
- Use ONLY the provided sentence; do not add external facts.
- Be concise and avoid redundancy.
- No markdown fences. No prose outside JSON.
- Return a COMPACT JSON object (no indentation, no newlines, no spaces between elements).
- If nothing can be extracted, return {{"qualities": []}}.
[/INST]
{examples}
</s>
[INST]sentence:{user_query}[/INST]
"""

def _render_examples(examples: Iterable[dict[str, str]]) -> str:
    """Render few-shot examples block used by the prompt."""
    # i.e., instead of a dict for each example, we want a string block like:
    # sentence: "Data Preprocessing is subclass of Data Science Task"
    # {
    # "qualities": ["Data Preprocessing is subclass of Data Science Task"]
    # }
    block: list[str] = []
    for ex in examples:
        sent = ex["sentence"].replace('"', "")
        out  = ex["output"]
        block.append(
            # f'sentence: "{sent}"\n{{\n"qualities": {out}\n}}'
            f'sentence: "{sent}"\n{{"qualities": {out}}}'
        )
    return "\n\n".join(block) # double newlines between examples

    # The final rendered examples string looks like:
    # sentence: "Data Preprocessing is subclass of Data Science Task"
    # {
    # "qualities": ["Data Preprocessing is subclass of Data Science Task"]
    # }
    #
    # sentence: "Transparency Property of an →KI system ..."
    # {
    # "qualities": ["Transparency is a property of KI system.", "Transparency is explainable.", ...]
    # }

PROMPT: PromptTemplate = PromptTemplate.from_template(_PROMPT_TEMPLATE)

# ---------- Parsing helpers ----------
# _JSON_OBJECT_RE = re.compile(r"\{(?:[^{}]|(?R))*\}", flags=re.DOTALL)
# # Recursive regex to match balanced {...} JSON objects.

# def _first_json_object(text: str) -> str | None:
#     """Return the first balanced {...} JSON object substring, if any."""
#     m = _JSON_OBJECT_RE.search(text)
#     return m.group(0) if m else None # group 0 is the full match

# def _first_json_object(text: str) -> str | None:
#     """Return the first balanced {...} JSON object substring, if any."""
#     stack = []
#     start = None
#     for i, c in enumerate(text):
#         if c == '{':
#             if not stack:
#                 start = i
#             stack.append(c)
#         elif c == '}':
#             if stack:
#                 stack.pop()
#                 if not stack and start is not None:
#                     # return the first complete JSON-like object
#                     return text[start:i+1]
#     return None

def _coerce_qualities(obj: Any) -> Qualities:
    """Validate and coerce arbitrary parsed JSON into Qualities."""
    if not isinstance(obj, dict):
        return []
    qualities = obj.get("qualities")
    if isinstance(qualities, list) and all(isinstance(q, str) for q in qualities):
        # normalize/trim
        return [q.strip() for q in qualities if q and isinstance(q, str)]
    return []

# ---------- Public API ----------
def build_sentence_decomposer(
    # llm: LLMResponder, 
    config: DecomposeConfig | None = None) -> TextDecomposer:
    """
    Create a callable `decompose_sentence(sentence: str) -> Qualities` bound to a given LLM.
    Use this to inject your LangChain chain (e.g., `prompt | get_response`).
    """
    cfg = config or DecomposeConfig()

    def decompose_sentence(sentence: str) -> Qualities:
        """
        Split a sentence into atomic "qualities" via LLM.
        Returns a list of short statements. Never raises on model formatting issues.
        """
        # sanitize the user sentence lightly for prompt robustness
        s = " ".join(sentence.splitlines()[: cfg.prompt_max_newlines]) # limit newlines
        s = s.replace('"', "") # remove quotes to avoid breaking prompt JSON
        prompt_str = PROMPT.format(
            examples=_render_examples(_EXAMPLES),
            user_query=f'"{s}"'
        )
        # `prompt_str` is unused here, but could be logged for debugging.
        # rich.print(f"Prompt string: {prompt_str}")
        print("Prompt string:", prompt_str)
        
        # Compose the chain
        # sentence_chain = PROMPT | llm_runnable
        # imagine it as passing PROMPT to the llm_runnable, but the PROMPT still has variables
        # than need to be filled in. So, we still have to invoke the sentence_chain with those variables. 
        # raw: str = sentence_chain.invoke({
        #     "examples": _render_examples(_EXAMPLES), 
        #     "user_query": f'"{s}"'
        # })
        # 1. In LangChain, `PromptTemplate` defines variables: [`examples`, `user_query`].
        # 2. When we call llm.invoke({...}), the chain automatically:
        #     - Substitutes those variables into the prompt template internally.
        #     - Passes the final string to the model.

        # Simply pass the prompt string to the llm directly (No LangChain chain here for simplicity of our case)
        # llm(prompt_str)
        # response = llm.invoke(prompt_str)
        
        # llm = get_llm_responder()
        # response = llm.invoke({
        #     "prompt": prompt_str,
        #     "max_tokens": 500,
        #     # "temperature": 0.2,
        # })
        # or for convenience
        response = respond(
            prompt_str, 
            max_tokens=500, 
            # temperature=0.2
        )
        # remove the prompt from the response
        print("LLM response:", response)
        response = response.replace(prompt_str, "").strip()
        print("LLM response after prompt removal:", response)

        # Some LangChain models return only the completion; if not, raw is fine.

        # 💚 Try strict parse → 🟠 fallback to slice → 🚨 fallback to empty list
        try:
            # remove literal \n, \r, and multiple spaces that appear between JSON punctuation
            response = response.replace("\n", "").replace("\r", "").strip()
            parsed = json.loads(response) # ideally, raw is: {"qualities": [...]}
            qualities = _coerce_qualities(parsed)
            if qualities:
                return qualities # a list[str]
        except Exception:
            pass

        # blob = _first_json_object(response)
        blob = _extract_json_object(response)
        if blob:
            blob_clean = blob.replace("\\n", "").replace("\\r", "")
            try:
                parsed = json.loads(blob)
                qualities = _coerce_qualities(parsed)
                if qualities:
                    return qualities
            except Exception:
                pass

        # Last resort: if the model dumped plain lines, split heuristically
        fallback = [line.strip("-• ").strip() for line in response.splitlines() if line.strip()]
        return fallback if fallback else []

    return decompose_sentence
