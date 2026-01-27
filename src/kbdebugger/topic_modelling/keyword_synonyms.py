from kbdebugger.prompts import render_prompt
from kbdebugger.llm.model_access import respond
from kbdebugger.utils import ensure_json_object
import rich


def generate_synonyms_for_keyword(keyword: str) -> list[str]:
    """
    Given a user-provided keyword, query an LLM to generate up to 10 semantically similar synonyms.

    Parameters
    ----------
    keyword:
        A single-word or short-phrase topic (e.g., "fairness", "explainability").

    Returns
    -------
    list[str]
        A list of synonym strings to be used in downstream semantic expansion.
    """
    prompt = render_prompt("keyword_synonyms", keyword=keyword)

    raw = respond(prompt, json_mode=True, temperature=0.0, max_tokens=512)
    obj = ensure_json_object(raw)
    synonyms = obj.get("synonyms", [])
    
    rich.print("[green][LLM Synonym Generation][/green] Generated synonyms:", synonyms)
    
    return synonyms
