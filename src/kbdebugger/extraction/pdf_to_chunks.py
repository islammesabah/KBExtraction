from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from kbdebugger.compat.langchain import (
    RecursiveCharacterTextSplitter,
    Document,
    PyMuPDFLoader, # use Docling
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------
def load_pdf_chunks(
    pdf_path: str | Path,
    chunk_size: int = 700,
    chunk_overlap: int = 70,
) -> List[Document]:
    """
    Load a PDF with PyMuPDFLoader and split it into raw character chunks.

    Each resulting chunk is a LangChain Document with:
    - page_content: the chunk text
    - metadata: at least 'source' and 'start_index' (from the TextSplitter)
    """
    pdf_path = Path(pdf_path)

    loader = PyMuPDFLoader(str(pdf_path))
    page_docs = loader.load()  # one Document per page

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )
    split_docs: List[Document] = splitter.split_documents(page_docs)

    logger.info(
        "Loaded %d chunks from PDF %s (chunk_size=%d, overlap=%d)",
        len(split_docs),
        pdf_path.name,
        chunk_size,
        chunk_overlap,
    )

    return split_docs


def clean_chunk_documents(
    docs: Iterable[Document],
) -> List[Document]:
    """
    Apply heuristic cleaning to each Document's text and return new Documents.

    Cleaning rules:
    - remove lines containing DOIs
    - remove lines starting with numbers like '1.' or '2:'
    - remove lines containing email addresses
    - remove lines with common boilerplate words (Received, Abstract, Keywords, etc.)
    - remove lines that are standalone numbers
    - fix hyphenated line breaks ('retrieval-\\n augmented' → 'retrievalaugmented')
    - collapse multiple whitespace characters into a single space
    """
    cleaned_docs: List[Document] = []

    for doc in docs:
        text = doc.page_content
        md = dict(doc.metadata)  # copy to avoid mutating original

        lines = text.split("\n")
        cleaned_lines: List[str] = []

        for line in lines:
            # Skip lines with DOIs
            if re.search(r"doi:\s*\d+\.\d+/\S+", line, re.IGNORECASE):
                continue

            # Skip lines starting with numbers followed by ':' or '.'
            if re.match(r"^\d+[:.]", line):
                continue

            # Skip lines containing email addresses
            if re.search(
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                line,
            ):
                continue

            # # Skip lines containing specific keywords
            # if re.search(
            #     r"(Received|revised|accepted|Keywords|Abstract)",
            #     line,
            #     re.IGNORECASE,
            # ):
            #     continue

            # Skip lines that are standalone numbers
            if re.match(r"^\d+$", line.strip()):
                continue

            # Fix hyphenated line breaks (e.g., "retrieval-\n augmented")
            line = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", line)

            # Replace multiple spaces with a single space
            line = re.sub(r"\s+", " ", line)

            cleaned_line = line.strip()
            if cleaned_line:
                cleaned_lines.append(cleaned_line)

        # cleaned_text = "\n".join(cleaned_lines)
        cleaned_text = " ".join(cleaned_lines)

        # Fix metadata semantics:
        source = md.get("source")
        start_index = md.get("start_index")

        new_metadata: Dict[str, Any] = dict(md)
        if start_index is not None:
            new_metadata["chunk_start_index"] = int(start_index)
        # If you don't really need fake page_number, don't add it.

        cleaned_docs.append(
            Document(
                page_content=cleaned_text,
                metadata=new_metadata,
            )
        )

    return cleaned_docs


# ---------------------------------------------------------------------------
# Public high-level API
# ---------------------------------------------------------------------------
def extract_pdf_chunks(
    pdf_path: str | Path,
    chunk_size: int = 700,
    chunk_overlap: int = 70,
) -> List[Document]:
    """
    High-level pipeline: PDF → larger cleaned text chunks (LangChain Documents).
    """
    pdf_path = Path(pdf_path)

    raw_docs = load_pdf_chunks(
        pdf_path=pdf_path,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    if not raw_docs:
        logger.warning("No text extracted from PDF: %s", pdf_path)
        return []

    cleaned_docs = clean_chunk_documents(raw_docs)
    return cleaned_docs
