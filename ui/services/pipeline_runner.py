from __future__ import annotations
import math

"""
Pipeline runner for the UI.

This module runs long stages in a background thread and reports progress
into the job store.

We start with Stage 2 (Docling + KeyBERT + Decomposer),
and we design the function so you can extend it to Stage 3/4
without changing the job API contract.
"""

from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from kbdebugger.pipeline.config import PipelineConfig
from kbdebugger.extraction.api import extract_paragraphs_from_pdf
from kbdebugger.extraction.logging import build_chunked_documents_payload

from kbdebugger.keyword_extraction.api import filter_paragraphs_by_keyword
from kbdebugger.keyword_extraction.logging import build_keybert_payload

from kbdebugger.extraction.api import decompose_paragraphs_to_qualities
# Optional next stages (enable when ready):
# from kbdebugger.subgraph_similarity.api import filter_qualities_by_subgraph_similarity
# from kbdebugger.novelty.comparator import classify_qualities_novelty
# from kbdebugger.graph.api import retrieve_keyword_subgraph

from ui.services.job_store import JOB_STORE
from ui.services.json_sanitize import to_jsonable
from ui.services.progress_callbacks import init_stage, make_job_progress_callback

def run_pipeline(
    *,
    job_id: str,
    file_path: Path,
    keyword: str,
    cfg: PipelineConfig,
) -> Dict[str, Any]:
    """
    Run Stage 2 end-to-end and return JSON-serializable output.

    Parameters
    ----------
    job_id:
        Job identifier whose progress should be updated.
    file_path:
        Path to the uploaded document.
    keyword:
        User-selected Trustworthy AI pillar keyword.
    cfg:
        Central PipelineConfig (from_env).

    Returns
    -------
    dict
        JSON payload for the UI.
    """
    JOB_STORE.set_running(job_id)

    # ---------------------------
    # Stage 2a: Docling
    # ---------------------------
    init_stage(
        job_id=job_id,
        stage="Docling",
        message="🦆 Parsing document into paragraphs (Docling)...",
        current=None,
        total=None,
    )

    paragraphs, docling_log = extract_paragraphs_from_pdf(
        pdf_path=str(file_path),
        do_ocr=cfg.docling_enable_OCR,
        do_table_structure=cfg.docling_enable_table_recognition,
    )

    # ---------------------------
    # Stage 2b: KeyBERT filter
    # ---------------------------
    total_par = len(paragraphs)
    init_stage(
        job_id=job_id,
        stage="KeyBERT",
        message=f"KeyBERT: 🔎 Scanning {total_par} paragraphs for keyword '{keyword}'...",
        current=0,
        total=total_par,
    )

    keybert_result, keybert_log = filter_paragraphs_by_keyword(
        paragraphs=paragraphs,
        search_keyword=keyword,
        progress=make_job_progress_callback(job_id=job_id, stage="KeyBERT"),
    )
        
    matched_docs = keybert_result.matched_docs

    # ---------------------------
    # Stage 2c: LLM Decomposer
    # ---------------------------
    # NOTE: total here depends on our decomposer loop granularity:
    # - if progress reports batches: total = num_batches
    # - if progress reports paragraphs: total = len(matched_docs)
    num_batches = math.ceil(len(matched_docs) / 5) # TODO: change 5 if batch size changed!
    init_stage(
        job_id=job_id,
        stage="DecomposerLLM",
        message=f"🧷 LLM Decomposer: Decomposing {len(matched_docs)} matched paragraphs into qualities..",
        current=0,
        total=num_batches,
    )

    qualities, decomposer_log = decompose_paragraphs_to_qualities(
        paragraphs=list(matched_docs),
        progress=make_job_progress_callback(job_id=job_id, stage="DecomposerLLM")
    )

    response = {
        "Docling": docling_log,
        "KeyBERT": keybert_log,
        "DecomposerLLM": decomposer_log,
    }

    return to_jsonable(response)
