from __future__ import annotations

"""
Pipeline runner for KBDebugger.

This module intentionally contains **no algorithmic logic**.
It is a thin orchestration layer that wires together the already-implemented
pipeline stages via their public APIs.

Design principles
-----------------
- **No heavy computation here** (no embedding, no indexing, no parsing).
- **No stage internals here** (no manual model construction, no method-level plumbing).
- **Clear stage boundaries**: each stage is called as a single function.
- **Research-friendly readability**: the pipeline reads like a methods section.

End-to-end stages
-----------------
1) KG subgraph retrieval:
    Retrieve KG relations around a keyword.

2) Corpus → qualities:
    Load corpus, chunk it, and decompose into atomic "quality" sentences.

3) Vector similarity filter:
    Compare qualities against KG relation sentences; keep only high-similarity items.

4) Novelty comparator (LLM):
    Classify each kept quality as EXISTING / PARTIALLY_NEW / NEW.

5) Triplet extraction (LLM):
    Extract S-P-O triplets for qualifying novelty decisions (env-controlled policy).

6) Human oversight:
    Show extracted relations to a human reviewer; upsert accepted ones into the KG;
    log accepted/rejected decisions.

This module should remain stable and boring.
🧪 All experimental work should happen inside stage APIs, not here.
"""

import rich
from kbdebugger.graph.api import (
    retrieve_keyword_subgraph,
    upsert_extracted_triplets
)
from kbdebugger.extraction.api import (
    extract_paragraphs_from_pdf,
    decompose_paragraphs_to_qualities,
)
from kbdebugger.keyword_extraction.api import filter_paragraphs_by_keyword
from kbdebugger.subgraph_similarity.api import filter_qualities_by_subgraph_similarity
from kbdebugger.novelty.comparator import classify_qualities_novelty
from kbdebugger.extraction.triplet_extraction_batch import extract_triplets_from_novelty_results
from kbdebugger.human_oversight.api import run_human_oversight
from .config import PipelineConfig
from kbdebugger.utils.run_timing import RunTimer

def run_pipeline(cfg: PipelineConfig) -> None:
    """
    Orchestrate the full KBDebugger pipeline.

    Parameters
    ----------
    cfg:
        PipelineConfig instance (typically constructed via PipelineConfig.from_env()).

    Notes
    -----
    This function intentionally returns None.
    Persistence happens via:
    - Neo4j upserts (for accepted relations)
    - JSON logs emitted by individual stages

    Raises
    ------
    ValueError
        If a stage produces an empty or invalid output that prevents downstream stages
        from meaningfully operating (e.g., no KG relations retrieved, no qualities extracted).
    """
    timer = RunTimer(run_name="kbdebugger_pipeline")

    # ---------------------------------------------------------------------
    # Stage 1: Retrieve KG subgraph relations (reference set for similarity)
    # ---------------------------------------------------------------------
    with timer.stage("💧 Neo4j: retrieve_keyword_subgraph"):
        kg_relations = retrieve_keyword_subgraph(
            keyword=cfg.kg_retrieval_keyword,
            limit_per_pattern=cfg.kg_limit_per_pattern,
        )

    # ---------------------------------------------------------------------
    # Stage 2: Extract candidate qualities
    # ---------------------------------------------------------------------
    # Stage 2a: PDF -> paragraphs
    with timer.stage("🦆 Docling: extract_paragraphs_from_pdf"):
        paragraphs = extract_paragraphs_from_pdf(
            pdf_path=cfg.corpus_path,
            do_ocr=cfg.docling_enable_OCR,
            do_table_structure=cfg.docling_enable_table_recognition,
        )

    # Stage 2b: keyword extraction (KeyBERT gate) to find matching paragraphs to the user-chosen keyword
    with timer.stage("🔎 KeyBERT: filter_paragraphs_by_keyword"):
        keybert_result = filter_paragraphs_by_keyword(
            paragraphs=paragraphs,
            search_keyword=cfg.kg_retrieval_keyword,
        )

    with timer.stage("🧷 LLM Decomposer: decompose_paragraphs_to_qualities"):
        # Stage 2c: matched paragraphs -> qualities
        candidate_qualities = decompose_paragraphs_to_qualities(
            paragraphs=keybert_result.matched_docs,
        )

    # ---------------------------------------------------------------------
    # Stage 3: Vector similarity filtering (kept qualities + neighbor context)
    # ---------------------------------------------------------------------
    with timer.stage("🧠 Vector similarity filter"):
        kept, _dropped = filter_qualities_by_subgraph_similarity(
            kg_relations=kg_relations,
            qualities=candidate_qualities,
            cfg=cfg.vector_similarity,
            pretty_print=False,
        )

    # ---------------------------------------------------------------------
    # Stage 4: Novelty decision (LLM comparator)
    # ---------------------------------------------------------------------
    with timer.stage("🧪 LLM Novelty comparator"):
        novelty_results = classify_qualities_novelty(
            kept,
            max_tokens=cfg.novelty_llm_max_tokens,
            temperature=cfg.novelty_llm_temperature,
            pretty_print=False,
            # use_batch=True
            # batch_size=5
        )

    # # ---------------------------------------------------------------------
    # # Stage 5: Human oversight via UI
    # # ---------------------------------------------------------------------
    # 🖌️ In the UI, here we will show:
    # - 3 tabs: Existing, Partially New, New
    # - Each tab shows quality sentences that were classified into that category.
    # The user can then select which sentences to extract triplets from.
    # then the selected sentences (i.e., List[QualityNoveltyResult]) are passed to the triplet extraction stage.


    # ---------------------------------------------------------------------
    # Stage 6: Triplet extraction (policy-controlled via env)
    # ---------------------------------------------------------------------
    with timer.stage("🧾 Triplet extraction"):
        extracted_triplets = extract_triplets_from_novelty_results(
            # 🖌️ here the novelty results are what the user has selected for extraction based on their novelty decision 
            # (e.g., they may only want to extract from "New" sentences, 
            # or they may want to extract from both "Partially New" and "New" sentences, etc.)
            novelty_results, 
            batch_size=cfg.triplet_extraction_batch_size,
        )

    # ---------------------------------------------------------------------
    # Stage 7: KG Upsert
    # ---------------------------------------------------------------------
    # 🖌️ Here we upsert the relations
    # for extraction in extracted_triplets:
    #     # extracted_triplets is like a list of list of triplets with provenance.
    #     # So, each `extraction` corresponds to one quality sentence that we extracted triplets from
    #     graph_relations = map_extracted_triplets_to_graph_relations(extraction)
    #     graph = get_graph()
    #     graph.upsert_relations(graph_relations)

    # with timer.stage("🧠 Neo4j upsert_extracted_triplets"):
    #     upsert_extracted_triplets(
    #         extractions=extracted_triplets,
    #         # provenance: we can store the PDF filename as the source of these extracted relations
    #         source=cfg.corpus_path,  
    #     )

    timing_path = timer.save_json()
    rich.print(f"[INFO] ⏱️ Wrote pipeline timing log to {timing_path}")

    # # ---------------------------------------------------------------------
    # # Stage 6: Human oversight + KG upsert + decision logging
    # # ❌ DEPRECATED
    # # ---------------------------------------------------------------------
    # oversight_result = run_human_oversight(extracted_relations)

    # graph = get_graph()
    # graph.upsert_relations(
    #     oversight_result.accepted,
    #     pretty_print=True,
    # )
