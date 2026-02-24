from __future__ import annotations
from encodings.punycode import T
from typing import List, Optional

from kbdebugger.compat.langchain import Document
from kbdebugger.types.ui import ProgressCallback

# from .chunk import chunk_corpus
from .decompose import decompose_documents
from .types import DecomposeMode, Qualities
from .pdf_to_paragraphs import extract_paragraphs_with_docling


# 1. 🦆 Docling: PDF → paragraphs (list[str])
def extract_paragraphs_from_pdf(
    *,
    pdf_path: str,
    do_ocr: bool = True,
    do_table_structure: bool = True,
) -> tuple[List[Document], dict]:
    """
    Public API: Extract clean paragraphs from a PDF via 🦆 Docling.

    Guarantees
    ----------
    - Returned Documents always have non-empty `page_content`
    - Order is preserved
    - All metadata is preserved

    This function establishes a strong invariant for downstream stages.

    Returns
    -------
    tuple[List[Document], dict]
        A tuple of (List[Document], log_payload), where:
        - List[Document] is a list of LangChain Document objects, one per paragraph, with metadata.
        - log_payload is a dictionary containing metadata for logging.
    """
    paragraphs, log_payload = extract_paragraphs_with_docling(
        pdf_path=pdf_path,
        do_ocr=do_ocr,
        do_table_structure=do_table_structure,
    )

    # paragraphs = [
    #     doc.page_content.strip()
    #     for doc in paragraph_docs
    #     if doc.page_content and doc.page_content.strip()
    # ]

    paragraphs = [
        doc
        for doc in paragraphs
        if doc.page_content and doc.page_content.strip()
    ]

    if not paragraphs:
        raise ValueError("🦆 Docling extraction produced no valid paragraphs.")
    
    return paragraphs, log_payload


# 2. LLM decomposer: paragraphs → qualities (sentences)
def decompose_paragraphs_to_qualities(
    *,
    paragraphs: List[Document],
    progress: Optional[ProgressCallback] = None,
    # mode: str = "paragraph",
) -> tuple[Qualities, dict]:
    """
    Public API: Decompose paragraphs into atomic qualities.

    Parameters
    ----------
    paragraphs:
        Paragraph Documents to be decomposed by the LLM decomposer.

    Returns
    -------
    tuple[Qualities, dict]
        The extracted qualities and the decomposer log payload.
    """
    # Reuse existing decomposer by wrapping paragraphs into the expected "docs" shape.
    # If `decompose_documents` expects LangChain Documents, create them here.
    # Otherwise, pass the list[str] directly if supported.
    qualities, decomposer_log = decompose_documents(
        docs=paragraphs, 
        mode=DecomposeMode.CHUNKS,
        progress=progress
    )

    # if not qualities:
    #     raise ValueError("Decomposition produced no qualities.")
    
    return qualities, decomposer_log
