from __future__ import annotations

from pathlib import Path
from typing import List
from kbdebugger.extraction.types import SourceKind
import rich

from langchain_docling.loader import DoclingLoader

from kbdebugger.compat.langchain import (
    Document,
)

# from docling.datamodel.base_models import InputFormat
# from docling.datamodel.pipeline_options import PdfPipelineOptions
# from docling.document_converter import DocumentConverter, PdfFormatOption

from .logging import save_chunked_documents_json


def extract_paragraphs_with_docling(
        pdf_path: str | Path,
        do_ocr: bool = False,
        do_table_structure: bool = False
    ) -> tuple[List[Document], dict]:
    """
    Extract paragraph-level text chunks from a PDF using Docling via LangChain.
    👁️ Configurable for OCR and table recognition via .env.

    Parameters
    ----------
    pdf_path : str | Path
        Path to the input PDF file.

    Returns
    -------
    tuple[List[Document], dict]
        A tuple of (List[Document], logging_payload), where:
        - List[Document] is a list of LangChain Document objects, one per paragraph, with metadata.
        - logging_payload is a dictionary containing metadata for logging.

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
    # pipeline_options = PdfPipelineOptions(
    #     do_ocr=do_ocr,
    #     do_table_structure=do_table_structure,
    # )

    # converter = DocumentConverter(format_options={
    #     InputFormat.PDF: PdfFormatOption(
    #         pipeline_options=pipeline_options,
    #         # backend=DoclingParseV2DocumentBackend  # disables layout AI
    #     )
    # })

    # pdf_options = PdfPipelineOptions(do_ocr=do_ocr, do_table_structure=do_table_structure)

    # doc_converter = DocumentConverter(
    #     format_options={
    #         InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)
    #     }
    # )

    loader = DoclingLoader(
        str(pdf_path),
        # converter=doc_converter
    )

    docs: List[Document] = loader.load()

    rich.print("\n\n===> 🦆 Docling extraction complete <===")
    rich.print(f"👁️  [DOCLING] OCR enabled: {do_ocr}")
    rich.print(f"📊  [DOCLING] Table recognition enabled: {do_table_structure}")

    logging_payload = save_chunked_documents_json(docs=docs, source_kind=SourceKind.PDF_PARAGRAPHS)

    return docs, logging_payload
