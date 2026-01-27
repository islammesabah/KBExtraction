from __future__ import annotations

from pathlib import Path
from typing import List
from kbdebugger.extraction.types import SourceKind
import rich

from langchain_core.documents import Document
from langchain_docling.loader import DoclingLoader

from .logging import save_chunked_documents_json


def extract_paragraphs_with_docling(pdf_path: str | Path) -> List[Document]:
    """
    Extract paragraph-level text chunks from a PDF using Docling via LangChain.

    Parameters
    ----------
    pdf_path : str | Path
        Path to the input PDF file.

    Returns
    -------
    List[Document]
        A list of LangChain Document objects, one per paragraph, with metadata.

    Notes
    -----
    - This function does not perform any post-cleaning or filtering.
    - Docling automatically detects layout and produces high-quality chunks.
    - Each paragraph is treated as a standalone Document.

    Example
    -------
    >>> docs = extract_paragraphs_with_docling("/path/to/my.pdf")
    >>> print(docs[0].page_content)
    "First paragraph from the PDF..."
    """
    loader = DoclingLoader(str(pdf_path))
    docs: List[Document] = loader.load()
    for d in docs:
        # d.metadata["source"] = Path(d.metadata.get("source", "unknown")).name
        rich.print(f" - {d.page_content=}")


    save_chunked_documents_json(docs=docs, source_kind=SourceKind.PDF_PARAGRAPHS)

    return docs
