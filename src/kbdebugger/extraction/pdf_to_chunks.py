# import fitz  # PyMuPDF
# import re
# import spacy

# from kbdebugger.compat.langchain import RecursiveCharacterTextSplitter, Document, PyMuPDFLoader, UnstructuredPDFLoader
# import logging
# import os

# # def extract_text_with_metadata(pdf_path):
# #     loader = UnstructuredPDFLoader(pdf_path)
# #     data = loader.load()
# #     text_splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=70, add_start_index=True)
# #     return text_splitter.split_documents(data)

# def extract_text_with_metadata(pdf_path):
#     loader = PyMuPDFLoader(pdf_path)  # instead of UnstructuredPDFLoader
#     # .load() will load each page as a separate LangChain Document with page_content and metadata
#     data = loader.load()
#     # Splitting text by recursively looking at characters.
#     # Recursively tries to split by different characters to find one that works.
#     # Cuts the text into chunks of ~700 characters with ~70 overlap
#     splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=70, add_start_index=True)
#     return splitter.split_documents(data)


# def clean_extracted_text(chunks):
#     cleaned_chunks = []

#     for chunk in chunks:
#         text = chunk.page_content
#         start_index = chunk.metadata['start_index']
#         source = chunk.metadata['source']
#         lines = text.split('\n')
#         cleaned_lines = []

#         for line in lines:
#             # Skip lines with DOIs
#             if re.search(r'doi:\s*\d+\.\d+/\S+', line, re.IGNORECASE):
#                 continue
#             # Skip lines starting with numbers followed by ':' or '.'
#             if re.match(r'^\d+[:.]', line):
#                 continue
#             # Skip lines containing email addresses
#             if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', line):
#                 continue
#             # Skip lines containing specific keywords
#             if re.search(r'(Received|revised|accepted|Keywords|Abstract)', line, re.IGNORECASE):
#                 continue
#             # Skip lines that are standalone numbers
#             if re.match(r'^\d+$', line.strip()):
#                 continue
#             # Optionally skip very short lines
#             # if len(line.strip()) < 20:
#                 # continue
#             # Fix hyphenated line breaks (e.g., "retrieval-\n augmented")
#             line = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', line)
#             # Replace multiple spaces with a single space
#             line = re.sub(r'\s+', ' ', line)
#             cleaned_lines.append(line.strip())

#         # Preserve paragraph breaks by joining with double newline
#         cleaned_text = '\n'.join(cleaned_lines) # can give \n\n
#         cleaned_chunks.append({
#             'source': source,
#             'start_index': start_index,
#             'cleaned_text': cleaned_text
#         })

#     return cleaned_chunks

# def structure_sentences(chunks):
#     documents = []
#     for chunk in chunks:
#         start_index = chunk['start_index']
#         source = chunk['source']
#         doc = Document(
#                 page_content=chunk['cleaned_text'],
#                 metadata={
#                     'page_number': start_index,
#                     'source': source
#                 }
#             )
#         documents.append(doc)
#     return documents

# def create_chunks(pdf_path):
#     docs = extract_text_with_metadata(pdf_path) 
#     if not docs:
#         print("No text extracted from the PDF.")
#         return

#     cleaned_chunks = clean_extracted_text(docs)

#     # Structure sentences using LangChain's Document with metadata
#     return structure_sentences(cleaned_chunks)

# ----------------------------------------------
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from kbdebugger.compat.langchain import (
    RecursiveCharacterTextSplitter,
    Document,
    PyMuPDFLoader,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RawChunk:
    """A raw text chunk produced by the text splitter."""
    text: str
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class CleanedChunk:
    """A cleaned chunk, ready to become a LangChain Document."""
    source: str
    start_index: int
    cleaned_text: str


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------
def load_pdf_chunks(
    pdf_path: str | Path,
    chunk_size: int = 700,
    chunk_overlap: int = 70,
) -> List[RawChunk]:
    """
    Load a PDF with PyMuPDFLoader and split it into raw character chunks.

    Each resulting chunk corresponds to a LangChain Document with:
    - page_content: the chunk text
    - metadata: at least 'source' and 'start_index' (from the TextSplitter)
    """
    pdf_path = Path(pdf_path)

    loader = PyMuPDFLoader(str(pdf_path))
    docs = loader.load() # will load each page as a separate Document

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )
    split_docs: List[Document] = splitter.split_documents(docs)

    raw_chunks: List[RawChunk] = [
        RawChunk(text=doc.page_content, metadata=dict(doc.metadata))
        for doc in split_docs
    ]

    logger.info(
        "Loaded %d chunks from PDF %s (chunk_size=%d, overlap=%d)",
        len(raw_chunks),
        pdf_path.name,
        chunk_size,
        chunk_overlap,
    )

    return raw_chunks


def clean_chunk_text(chunks: Iterable[RawChunk]) -> List[CleanedChunk]:
    """
    Apply heuristic cleaning to each chunk's text.

    Rules (same as your original clean_extracted_text):

    - remove lines containing DOIs
    - remove lines starting with numbers like '1.' or '2:'
    - remove lines containing email addresses
    - remove lines with common boilerplate words (Received, Abstract, Keywords, etc.)
    - remove lines that are standalone numbers
    - fix hyphenated line breaks ('retrieval-\\n augmented' → 'retrievalaugmented')
    - collapse multiple whitespace characters into a single space
    """
    cleaned: List[CleanedChunk] = []

    for chunk in chunks:
        text = chunk.text
        source = chunk.metadata.get("source", "Unknown source")
        start_index = int(chunk.metadata.get("start_index", 0))

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

            # Skip lines containing specific keywords
            if re.search(
                r"(Received|revised|accepted|Keywords|Abstract)",
                line,
                re.IGNORECASE,
            ):
                continue

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

        cleaned_text = "\n".join(cleaned_lines)

        cleaned.append(
            CleanedChunk(
                source=source,
                start_index=start_index,
                cleaned_text=cleaned_text,
            )
        )

    return cleaned


def chunks_to_documents(
    chunks: Iterable[CleanedChunk],
    pdf_path: Optional[str | Path] = None,
) -> List[Document]:
    """
    Convert cleaned chunks into LangChain Document objects.

    Metadata includes:
    - 'source'             : PDF filename or title
    - 'page_number'        : kept for backward compatibility — stores start_index
    - 'chunk_start_index'  : explicit name for the same value
    - 'pdf_path'           : full path, if provided
    """
    documents: List[Document] = []
    pdf_path_str = str(pdf_path) if pdf_path is not None else None

    for chunk in chunks:
        metadata: Dict[str, Any] = {
            "source": chunk.source,
            # Backwards compatible key name:
            "page_number": chunk.start_index,
            # New, clearer key:
            "chunk_start_index": chunk.start_index,
        }
        if pdf_path_str is not None:
            metadata["pdf_path"] = pdf_path_str

        documents.append(
            Document(
                page_content=chunk.cleaned_text,
                metadata=metadata,
            )
        )

    return documents


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

    Parameters
    ----------
    pdf_path:
        Path to the input PDF.
    chunk_size:
        Target character length of each chunk.
    chunk_overlap:
        Overlap between neighbouring chunks, in characters.

    Returns
    -------
    List[Document]
        One Document per cleaned chunk.
    """
    pdf_path = Path(pdf_path)

    raw_chunks = load_pdf_chunks(
        pdf_path=pdf_path,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    if not raw_chunks:
        logger.warning("No text extracted from PDF: %s", pdf_path)
        return []

    cleaned_chunks = clean_chunk_text(raw_chunks)
    return chunks_to_documents(cleaned_chunks, pdf_path=pdf_path)

__all__ = [
    "RawChunk",
    "CleanedChunk",
    "load_pdf_chunks",
    "clean_chunk_text",
    "chunks_to_documents",
    "extract_pdf_chunks",
]