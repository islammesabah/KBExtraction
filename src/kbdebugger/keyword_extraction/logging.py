from __future__ import annotations

from typing import Any, Dict, List, Optional

from kbdebugger.utils.time import now_utc_compact, now_utc_human
from kbdebugger.keyword_extraction.types import ParagraphMatch
from .types import KeyBERTConfig
from kbdebugger.utils.json import write_json

import rich

def build_keybert_payload(
    *,
    matched: List[ParagraphMatch],
    unmatched: List[ParagraphMatch],
    keyword: str,
    synonyms: Optional[List[str]],
    config: KeyBERTConfig,
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a clean, JSON-serializable KeyBERT results payload.

    Design goals
    ------------
    - Identical structure for:
        * log files
        * API responses (pipeline_runner)
    - Human-readable timestamp
    - Explicit counts for traceability

    Parameters
    ----------
    matched:
        Paragraphs classified as matched.
    unmatched:
        Paragraphs classified as not matched.
    keyword:
        User-selected keyword.
    synonyms:
        Generated keyword synonyms (if any).
    config:
        KeyBERT configuration used.
    created_at:
        Optional timestamp override (defaults to now_utc_human()).

    Returns
    -------
    Dict[str, Any]
        Clean payload ready for logging or API response.
    """
    created_at = created_at or now_utc_human()

    num_matched = len(matched)
    num_unmatched = len(unmatched)

    payload: Dict[str, Any] = {
        "created_at": created_at,
        "keyword": keyword,
        "generated_synonyms": synonyms or [],
        "num_total_paragraphs": num_matched + num_unmatched,
        "num_matched": num_matched,
        "num_unmatched": num_unmatched,
        "keyBERT_config": config.__dict__,
        "matched": [m.__dict__ for m in matched],
        "unmatched": [u.__dict__ for u in unmatched],
    }

    return payload


def save_keybert_result(
        *,
        matched: List[ParagraphMatch],
        unmatched: List[ParagraphMatch],
        keyword: str,
        synonyms: Optional[List[str]] = None,
        config: KeyBERTConfig,
        output_dir: str = "logs",
) -> Dict[str, Any]:
    """
    Save full KeyBERT paragraph match results including matched and unmatched paragraphs.

    Returns
    -------
    Dict[str, Any]
        The payload that was written to disk (useful for reuse).
    """
    payload = build_keybert_payload(
        matched=matched,
        unmatched=unmatched,
        keyword=keyword,
        synonyms=synonyms,
        config=config,
    )

    # Compact timestamp ONLY for filename
    timestamp_compact = now_utc_compact()
    out_path = (
        f"{output_dir}/01.1.6_keybert_paragraph_matched_paragraphs_"
        f"[{keyword}]_{timestamp_compact}.json"
    )

    write_json(out_path, payload)
    rich.print(f"[INFO] Saved KeyBERT matched paragraphs to {out_path}")

    return payload
