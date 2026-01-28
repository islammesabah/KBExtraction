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

from kbdebugger.graph.api import retrieve_keyword_subgraph
from kbdebugger.graph import get_graph
# from kbdebugger.extraction.api import extract_qualities_from_corpus
from kbdebugger.extraction.pdf_to_paragraphs import extract_paragraphs_with_docling
from kbdebugger.topic_modelling.BERTopic import extract_topics_from_paragraphs
from kbdebugger.topic_modelling.keyBERT import run_keybert_matching 
from kbdebugger.topic_modelling.keyword_synonyms import generate_synonyms_for_keyword

from kbdebugger.vector.api import run_vector_similarity_filter
from kbdebugger.novelty.comparator import classify_qualities_novelty
from kbdebugger.extraction.triplet_extraction_batch import extract_triplets_from_novelty_results
from kbdebugger.human_oversight.api import run_human_oversight
from .config import PipelineConfig


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
    # ---------------------------------------------------------------------
    # Stage 1: Retrieve KG subgraph relations (reference set for similarity)
    # ---------------------------------------------------------------------
    kg_relations = retrieve_keyword_subgraph(
        keyword=cfg.kg_retrieval_keyword,
        limit_per_pattern=cfg.kg_limit_per_pattern,
    )

    # ---------------------------------------------------------------------
    # Stage 2: Extract candidate qualities from corpus (chunk + decompose)
    # ---------------------------------------------------------------------
    # candidate_qualities = extract_qualities_from_corpus(
    #     source_kind=cfg.source_kind,
    #     path=cfg.corpus_path,
    # )

    paragraph_docs = extract_paragraphs_with_docling(
        pdf_path=cfg.corpus_path,
        do_ocr=cfg.docling_enable_OCR,
        do_table_structure=cfg.docling_enable_table_recognition
    )

    # extract only page_content from each Document:
    paragraphs = [d.page_content for d in paragraph_docs if d.page_content and d.page_content.strip()]
    # print(f"BERTopic input paragraphs: {len(paragraphs)} (example len={len(paragraphs[0]) if paragraphs else 0})")

    # Extract synonyms from LLM
    synonyms = generate_synonyms_for_keyword(cfg.kg_retrieval_keyword)

    matched, unmatched = run_keybert_matching(
        paragraphs=paragraphs,
        search_keyword=cfg.kg_retrieval_keyword,
        synonyms=synonyms
    )

    # topic_matches, topic_model = extract_topics_from_paragraphs(
    #     paragraphs=paragraphs,
    #     keyword=cfg.kg_retrieval_keyword,
    #     synonyms=synonyms
    # )


    # # ---------------------------------------------------------------------
    # # Stage 3: Vector similarity filtering (kept qualities + neighbor context)
    # # ---------------------------------------------------------------------
    # kept, _dropped = run_vector_similarity_filter(
    #     kg_relations=kg_relations,
    #     qualities=candidate_qualities,
    #     cfg=cfg.vector_similarity,
    #     pretty_print=True,
    # )

    # # ---------------------------------------------------------------------
    # # Stage 4: Novelty decision (LLM comparator)
    # # ---------------------------------------------------------------------
    # novelty_results = classify_qualities_novelty(
    #     kept,
    #     max_tokens=cfg.novelty_llm_max_tokens,
    #     temperature=cfg.novelty_llm_temperature,
    # )

    # # ---------------------------------------------------------------------
    # # Stage 5: Triplet extraction (policy-controlled via env)
    # # ---------------------------------------------------------------------
    # extracted_relations = extract_triplets_from_novelty_results(
    #     novelty_results,
    #     batch_size=cfg.triplet_extraction_batch_size,
    # )


    # # ---------------------------------------------------------------------
    # # Stage 6: Human oversight + KG upsert + decision logging
    # # ---------------------------------------------------------------------
    # oversight_result = run_human_oversight(extracted_relations)

    # graph = get_graph()
    # graph.upsert_relations(
    #     oversight_result.accepted,
    #     pretty_print=True,
    # )
