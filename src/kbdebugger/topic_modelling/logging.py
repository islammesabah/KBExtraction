import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
import pandas as pd

from bertopic._bertopic import BERTopic

from kbdebugger.utils.json import write_json, now_utc_compact
from kbdebugger.compat.langchain import Document


def save_topic_modeling_results(
    *,
    topic_model: BERTopic,
    documents: List[str],
    document_chunks: Optional[List[Document]] = None,
    keyword: str,
    matched_topic_ids: List[int],
    match_type_by_topic: Dict[int, str],
    matched_synonyms: Dict[int, set[str]],
    generated_synonyms: Optional[List[str]] = None,
    output_dir: Union[str, Path] = "logs",
) -> None:
    """
    Save full BERTopic modeling output and keyword match metadata to JSON for inspection.

    Parameters
    ----------
    topic_model: BERTopic
        The trained topic model.
    documents: list of str
        The raw input texts fed into the model.
        i.e., the output of Docling before topic modeling.

    document_chunks: list of LangChain Documents, optional
        If available, include their metadata in the output.
    keyword: str
        The user-specified keyword for topic matching.
    matched_topic_ids: list of int
        Topics selected for retention.
    match_type_by_topic: dict
        Topic ID -> "exact" or "synonym"
    matched_synonyms: dict
        Topic ID -> which synonym matched.
    generated_synonyms: list of str, optional
        If LLM was used, log the generated synonym list.
    output_dir: str or Path
        Directory to save the log file in.
    """
    timestamp = now_utc_compact()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Metadata
    meta = {
        "created_at": timestamp,
        "keyword": keyword,
        "num_documents": len(documents),
        "num_topics": len(topic_model.get_topics()), # includes -1 (outliers)
        "matched_topic_ids": matched_topic_ids,
        "match_type_by_topic": match_type_by_topic, # e.g. {3: "exact", 7: "synonym"}
        "matched_synonyms": matched_synonyms, # e.g. {7: "explainable AI", ...}
        "generated_synonyms": generated_synonyms or [],
    }

    # Per-document results (includes topic, prob, representative etc.)
    doc_info_df: pd.DataFrame = topic_model.get_document_info(documents)
    """
    >>> topic_model.get_document_info(docs)

    Document                               Topic    Name                        Top_n_words                     Probability    ...
    I am sure some bashers of Pens...       0       0_game_team_games_season    game - team - games...          0.200010       ...
    My brother is in the market for...      -1     -1_can_your_will_any         can - your - will...            0.420668       ...
    Finally you said what you dream...      -1     -1_can_your_will_any         can - your - will...            0.807259       ...
    Think! It is the SCSI card doing...     49     49_windows_drive_dos_file    windows - drive - docs...       0.071746       ...
    1) I have an old Jasmine drive...       49     49_windows_drive_dos_file    windows - drive - docs...       0.038983       ...
    """

    doc_info = doc_info_df.to_dict(orient="records")

    # Optional original chunk metadata
    chunk_metadata = None
    if document_chunks:
        chunk_metadata = [
            {
                "page_content": doc.page_content,
                "metadata": doc.metadata,
            } for doc in document_chunks
        ]

    # Topic summary info (counts, top_n_words, etc.)
    topic_info_df: pd.DataFrame = topic_model.get_topic_info() # BERTopic's topic summary
    # >>> topic_model.get_topic_info()

    # Topic   Count   Name
    # -1      4630    -1_can_your_will_any
    # 0       693     49_windows_drive_dos_file
    # 1       466     32_jesus_bible_christian_faith
    # 2       441     2_space_launch_orbit_lunar
    # 3       381     22_key_encryption_keys_encrypted

    topic_info = topic_info_df.to_dict(orient="records")

    payload: Dict[str, Any] = {
        "meta": meta,
        "topic_info": topic_info,  # Get all topic information
        "document_info": doc_info, # Get all document information
        "document_chunks": chunk_metadata,
    }

    out_path = output_dir / f"01.1.5_topic_modeling_summary_{keyword}_{timestamp}.json"
    write_json(out_path, payload)

    print(f"\n[INFO] Wrote topic modeling summary to {out_path}")
