from __future__ import annotations

"""
Minimal entry point to test the Extractor component in isolation.

Pipeline:
    1. Load documents from a text or PDF corpus & chunk them (Chunker).
    2. Decompose each document into atomic sentences/qualities (Decomposer).
    3. Extract S-P-O triplets for each atomic sentence (Triplet Extractor).
    4. Print or optionally write results to a JSON file.

Configuration is driven by environment variables (see ExtractorConfig.from_env).
"""

import json
import os
from dataclasses import dataclass
from typing import Literal, Tuple, List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()

from kbdebugger.utils.warnings_config import install_warning_filters
from kbdebugger.compat.langchain import Document

from kbdebugger.extraction.text_to_sentences import extract_txt_sentences
# from kbdebugger.extraction.pdf_to_sentences import extract_pdf_sentences
from kbdebugger.extraction.pdf_to_chunks import extract_pdf_chunks

from kbdebugger.extraction.decompose import decompose, DecomposeMode
from kbdebugger.extraction.triplet_extraction_batch import extract_triplets_batch
from kbdebugger.types import ExtractionResult, SourceKind
from kbdebugger.extraction.types import Qualities

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExtractorConfig:
    """
    Runtime configuration for the Extractor main script.

    Environment variables:

    - KB_SOURCE_KIND: one of
        * "TEXT"          → load plain-text file via `text_to_sentences`
        * "PDF_SENTENCES" → load PDF and split directly into sentences
        * "PDF_CHUNKS"    → load PDF and split into larger chunks

      Default: "TEXT"

    - KB_TEXT_PATH: path to txt file (used when KB_SOURCE_KIND == "TEXT")
      Default: "data/DSA/DSA_knowledge.txt"

    - KB_PDF_PATH: path to pdf file (used when KB_SOURCE_KIND starts with "PDF")
      Default: "data/SDS/example.pdf"

    - KB_BATCH_SIZE: number of atomic sentences per LLM batch for triplet extraction.
      Default: 5

    - KB_OUTPUT_PATH: optional path to write JSON results.
      If empty, results are only printed to stdout.
    """

    source_kind: SourceKind
    text_path: str
    pdf_path: str
    batch_size: int
    output_path: str | None

    @classmethod
    def from_env(cls) -> "ExtractorConfig":
        source_raw = os.getenv("KB_SOURCE_KIND", "TEXT").upper().strip()
        if source_raw not in {"TEXT", "PDF_SENTENCES", "PDF_CHUNKS"}:
            raise ValueError(f"Invalid KB_SOURCE_KIND={source_raw!r}")

        text_path = os.getenv("KB_TEXT_PATH", "data/DSA/DSA_knowledge.txt").strip()
        pdf_path = os.getenv("KB_PDF_PATH", "data/SDS/InstructCIR.pdf").strip()

        batch_size_str = os.getenv("KB_BATCH_SIZE", "5").strip()
        try:
            batch_size = max(1, int(batch_size_str))
        except ValueError:
            batch_size = 5

        output_raw = os.getenv("KB_OUTPUT_PATH", "").strip()
        output_path = output_raw or None

        return cls(
            source_kind=source_raw,  # type: ignore[arg-type]
            text_path=text_path,
            pdf_path=pdf_path,
            batch_size=batch_size,
            output_path=output_path,
        )

# ---------------------------------------------------------------------------
# High-level steps
# ---------------------------------------------------------------------------
def load_documents(cfg: ExtractorConfig) -> Tuple[List[Document], DecomposeMode]:
    """
    Use the Chunker submodule to load a corpus into LangChain Documents.
    Returns (documents, decompose_mode).
    """
    match cfg.source_kind:
        case "TEXT":
            docs = extract_txt_sentences(cfg.text_path)
            mode = DecomposeMode.SENTENCES

        # case "PDF_SENTENCES":
        #     docs = extract_pdf_sentences(cfg.pdf_path)
        #     mode = DecomposeMode.SENTENCES

        case "PDF_CHUNKS":
            docs = extract_pdf_chunks(cfg.pdf_path)
            mode = DecomposeMode.CHUNKS

    if not docs:
        raise ValueError("No documents loaded. Check your paths and source kind.")

    return (docs, mode)


def run_extractor(cfg: ExtractorConfig) -> List[ExtractionResult]:
    """
    End-to-end run of the Extractor component:

        Corpus -> Chunked Documents -> Atomic sentences/Qualities -> Triplets
    """
    # 1. Load corpus & chunk into LangChain Documents
    docs, mode = load_documents(cfg)

    # 2. Decompose each document into atomic sentences/qualities
    all_qualities: Qualities = []
    for doc in docs:
        qualities = decompose(text=doc.page_content, mode=mode)
        all_qualities.extend(qualities)

    if not all_qualities:
        raise ValueError("Decomposition produced no qualities.")

    # 3. Triplet extraction in batches
    results = extract_triplets_batch(all_qualities, batch_size=cfg.batch_size)
    return results


def print_results(results: List[ExtractionResult]) -> None:
    """
    Pretty-print extraction results to stdout using rich.
    """
    console.rule("[bold blue]Triplet Extraction Results")

    for i, item in enumerate(results, start=1):
        sentence: str = item.get("sentence", "")
        triplets: List[Tuple[str, str, str]] = item.get("triplets", [])

        # Header panel for each atomic sentence
        console.print(
            Panel.fit(
                Text(sentence, style="bold white"),
                title=f"[cyan]Sentence {i}",
                border_style="cyan",
            )
        )

        if not triplets:
            console.print("[yellow]No triplets extracted.[/yellow]\n")
            continue

        # Table of triplets
        table = Table(
            show_header=True,
            header_style="bold magenta",
            show_lines=True,
            border_style="dim",
        )
        table.add_column("Subject", style="green", ratio=2)
        table.add_column("Relation", style="white", ratio=3)
        table.add_column("Object", style="green", ratio=2)

        for subj, obj, rel in triplets:
            table.add_row(subj, rel, obj)

        console.print(table)
        console.print()  # extra newline


def save_results_json(results: List[ExtractionResult], path: str) -> None:
    """
    Write extraction results to a JSON file.
    """
    data = {
        "results": results,
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n[INFO] Wrote JSON results to {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    install_warning_filters()

    cfg = ExtractorConfig.from_env()
    console.rule("[bold green]KBDEBUGGER Extractor")

    console.print(f"[bold]Source kind:[/bold] [cyan]{cfg.source_kind}[/cyan]")
    if cfg.source_kind == "TEXT":
        console.print(f"[bold]Text path:[/bold] [white]{cfg.text_path}[/white]")
    else:
        console.print(f"[bold]PDF path:[/bold] [white]{cfg.pdf_path}[/white]")

    console.print(f"[bold]Batch size:[/bold] [yellow]{cfg.batch_size}[/yellow]")

    if cfg.output_path:
        console.print(f"[bold]Output file:[/bold] [green]{cfg.output_path}[/green]")

    console.print()  # spacing

    results = run_extractor(cfg)

    if cfg.output_path:
        save_results_json(results, cfg.output_path)

    print_results(results)


if __name__ == "__main__":
    main()