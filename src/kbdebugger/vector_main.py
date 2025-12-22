from __future__ import annotations

from kbdebugger.extraction.triplet_extraction_batch import extract_triplets_from_novelty_results
from kbdebugger.human_oversight.reviewer import review_triplets
from kbdebugger.novelty.types import NoveltyDecision

"""
Minimal entry point to test the Vector Similarity Filter component in isolation.

What this script validates
--------------------------
This script sanity-checks the end-to-end "Vector Similarity Filter" MVP:

1) Retrieve a keyword-guided subgraph from Neo4j (Graph Retriever).
2) Build a vector index over the KG subgraph relation sentences (r.sentence).
3) Load corpus (raw documents) and run only the Decomposer LLM to produce candidate qualities.
4) Filter qualities by vector similarity against the KG subgraph index.
5) Pretty-print kept/dropped results and optionally write them to JSON logs.

Important design decision
-------------------------
We intentionally DO NOT run triplet extraction here.

Triplet extraction is an expensive LLM step and is deferred until after
vector filtering. This script tests the cheaper filtering stage only.

Configuration
-------------
Driven by environment variables (see VectorMainConfig.from_env).

Typical usage:
    KB_KEYWORD=requirement KB_SOURCE_KIND=TEXT python -m kbdebugger.vector_main
"""

import os
from dataclasses import dataclass
from typing import cast

from rich.console import Console

from kbdebugger.extraction.types import SourceKind

from kbdebugger.extraction import chunk_corpus, decompose_documents
from kbdebugger.extraction.types import Qualities

from kbdebugger.graph.retriever import KnowledgeGraphRetriever

from kbdebugger.vector.encoder import SentenceTransformerEncoder
from kbdebugger.vector.similarity_filter import VectorSimilarityFilter

from kbdebugger.novelty.comparator import classify_qualities_novelty

console = Console()


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class VectorMainConfig:
    """
    Runtime configuration for vector_main.py.

    Environment variables
    ---------------------
    KB_KEYWORD:
        Keyword to retrieve a KG subgraph (Graph Retriever input).
        Default: "requirement"

    KB_SOURCE_KIND:
        One of:
            - "TEXT"
            - "PDF_SENTENCES"
            - "PDF_CHUNKS"
        Default: "TEXT"

    KB_TEXT_PATH:
        Text file path used when KB_SOURCE_KIND == "TEXT"
        Default: "data/DSA/DSA_knowledge.txt"

    KB_PDF_PATH:
        PDF path used when KB_SOURCE_KIND starts with "PDF"
        Default: "data/SDS/InstructCIR.pdf"

    KB_LIMIT_PER_PATTERN:
        How many KG relations to retrieve per pattern in KG retriever.
        Default: 50

    KB_TOP_K:
        How many nearest KG relations to retrieve per candidate quality.
        Default: 5

    KB_THRESHOLD:
        Minimum cosine similarity threshold.
        Default: 0.55

    KB_LOG_PATH:
        Optional JSON output path.
        Default: "logs/vector_similarity_results.json"
        Set empty to disable logging.
    """
    keyword: str
    source_kind: SourceKind
    text_path: str
    pdf_path: str

    limit_per_pattern: int
    top_k: int
    threshold: float

    log_path: str | None

    @classmethod
    def from_env(cls) -> VectorMainConfig:
        keyword = os.getenv("KB_KEYWORD", "requirement").strip()

        source_raw = os.getenv("KB_SOURCE_KIND", "TEXT").upper().strip()
        if source_raw not in {"TEXT", "PDF_SENTENCES", "PDF_CHUNKS"}:
            raise ValueError(f"Invalid KB_SOURCE_KIND={source_raw!r}")
        source_raw = cast(SourceKind, source_raw)

        text_path = os.getenv("KB_TEXT_PATH", "data/DSA/DSA_knowledge.txt").strip()
        pdf_path = os.getenv("KB_PDF_PATH", "data/SDS/Handout for inspection of examinations.pdf").strip()

        limit_per_pattern = int(os.getenv("KB_LIMIT_PER_PATTERN", "50").strip())
        top_k = int(os.getenv("KB_TOP_K", "5").strip())
        threshold = float(os.getenv("KB_THRESHOLD", "0.55").strip())

        log_raw = os.getenv("KB_LOG_PATH", "logs/vector_similarity_results.json").strip()
        log_path = log_raw or None

        return cls(
            keyword=keyword,
            source_kind=source_raw,
            text_path=text_path,
            pdf_path=pdf_path,
            limit_per_pattern=max(1, limit_per_pattern),
            top_k=max(1, top_k),
            threshold=threshold,
            log_path=log_path,
        )

# ---------------------------------------------------------------------------
def run_extractor(cfg: VectorMainConfig) -> Qualities:
    """
    Produce candidate qualities using ONLY the Decomposer module.

    This is intentionally cheaper than the full extractor pipeline and matches
    our improved design (triplet extraction happens later, only for kept qualities).
    """
    # 1. Load corpus & chunk into LangChain Documents
    docs, mode = chunk_corpus(
        source_kind=cfg.source_kind,
        path=cfg.text_path if cfg.source_kind == SourceKind.TEXT else cfg.pdf_path,
    )

    # 2. Decompose each document into qualities
    qualities = decompose_documents(
        docs=docs,
        mode=mode,
    )

    if not qualities:
        raise ValueError("Decomposition produced no qualities.")

    return qualities


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    cfg = VectorMainConfig.from_env()
    console.rule("[bold green]KBDEBUGGER Vector Similarity Filter")

    console.print(f"[bold]Keyword:[/bold] [cyan]{cfg.keyword}[/cyan]")
    console.print(f"[bold]Source kind:[/bold] [cyan]{cfg.source_kind}[/cyan]")
    console.print(f"[bold]Limit per retriever pattern:[/bold] [yellow]{cfg.limit_per_pattern}[/yellow]")
    console.print(f"[bold]top_k:[/bold] [yellow]{cfg.top_k}[/yellow]")
    console.print(f"[bold]threshold:[/bold] [yellow]{cfg.threshold}[/yellow]")
    if cfg.log_path:
        console.print(f"[bold]Log path:[/bold] [green]{cfg.log_path}[/green]")
    console.print()

    # 1) Retrieve KG subgraph relations around the keyword
    retriever = KnowledgeGraphRetriever(limit_per_pattern=cfg.limit_per_pattern)
    hits = retriever.retrieve(cfg.keyword)
    relations = [h["relation"] for h in hits]

    if not relations:
        console.print("[bold yellow]No KG relations retrieved. Try a different keyword.[/bold yellow]")
        return

    console.print(f"[bold]Retrieved KG relations:[/bold] [cyan]{len(relations)}[/cyan]")

    # 2) Produce candidate qualities (decomposer output)
    qualities = run_extractor(cfg)
    console.print(f"[bold]Candidate qualities (from decomposer):[/bold] [cyan]{len(qualities)}[/cyan]\n")

    # 3) Create encoder + filter component
    encoder = SentenceTransformerEncoder(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        device=None,          # let sentence-transformers choose
        normalize=True,       # recommended for cosine similarity
    )

    filt = VectorSimilarityFilter(
        encoder=encoder,
        top_k=cfg.top_k,
        threshold=cfg.threshold,
    )

    # 4) Build index over KG subgraph relation sentences
    index = filt.build_index(relations) # Here we internally encode the KG relations & build the index

    # 5) Filter qualities
    kept, dropped = filt.filter_qualities(index=index, qualities=qualities)

    # 6) Print results
    filt.pretty_print(kept=kept, dropped=dropped)

    novelty_results = classify_qualities_novelty(kept, max_tokens=700, temperature=0.0)

    extracted_triplets = extract_triplets_from_novelty_results(novelty_results)

    accepted, rejected = review_triplets(extracted_triplets)

if __name__ == "__main__":
    main()
