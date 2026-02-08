from __future__ import annotations
from encodings.punycode import T
from typing import List

from kbdebugger.compat.langchain import Document

from .chunk import chunk_corpus
from .decompose import decompose_documents
from .types import DecomposeMode, Qualities, SourceKind
from .pdf_to_paragraphs import extract_paragraphs_with_docling


# 1. 🦆 Docling: PDF → paragraphs (list[str])
def extract_paragraphs_from_pdf(
    *,
    pdf_path: str,
    do_ocr: bool = True,
    do_table_structure: bool = True,
) -> List[Document]:
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
    list[Document]
        Non-empty paragraph Documents, ready to feed into downstream stages
        (keyword extraction, LLM decomposition, etc.).
    """
    paragraphs = extract_paragraphs_with_docling(
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
    
    return paragraphs


# 2. LLM decomposer: paragraphs → qualities (sentences)
def decompose_paragraphs_to_qualities(
    *,
    paragraphs: List[Document],
    # mode: str = "paragraph",
) -> Qualities:
    """
    Public API: Decompose paragraphs into atomic qualities.

    Parameters
    ----------
    paragraphs:
        Paragraph Documents to be decomposed by the LLM decomposer.

    Returns
    -------
    Qualities
        The extracted qualities.
    """
    # Reuse existing decomposer by wrapping paragraphs into the expected "docs" shape.
    # If `decompose_documents` expects LangChain Documents, create them here.
    # Otherwise, pass the list[str] directly if supported.
    qualities = decompose_documents(docs=paragraphs, mode=DecomposeMode.CHUNKS)

    if not qualities:
        raise ValueError("Decomposition produced no qualities.")
    return qualities
