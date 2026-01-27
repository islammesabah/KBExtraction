from __future__ import annotations
import os
from .logging import save_chunked_documents_json

"""
kbdebugger.extraction public API.

Stage 1 (Chunking):
    Raw corpus file (.txt or .pdf) -> Chunked LangChain Documents
"""

from typing import Optional, Tuple, List
from .types import *

from kbdebugger.compat.langchain import Document
from kbdebugger.extraction.decompose import DecomposeMode
from kbdebugger.extraction.text_to_sentences import extract_txt_sentences
# from kbdebugger.extraction.pdf_to_sentences import extract_pdf_sentences
from kbdebugger.extraction.pdf_to_chunks import extract_pdf_chunks


def chunk_corpus(
        source_kind: SourceKind, 
        path: str,
) -> Tuple[List[Document], DecomposeMode]:
    """
    Chunk a raw corpus file into LangChain Documents.

    This is the first stage of the Extractor pipeline:
        Raw file -> Document chunks

    Parameters
    ----------
    source_kind:
        Determines how `path` is interpreted:
        - "TEXT":          plain-text file; output is sentence-like Documents
        - "PDF_SENTENCES": PDF split directly into sentence-like Documents
        - "PDF_CHUNKS":    PDF split into larger chunk Documents

    path:
        File path that corresponds to `source_kind`.

    Returns
    -------
    (docs, decompose_mode):
        docs:
            A list of LangChain Documents (chunks) ready for next stage (i.e., LLM Decomposer).
        decompose_mode:
            The recommended mode to pass to the Decomposer stage for each doc.
            This value is derived from the chunking granularity:
            - SENTENCES when docs are sentence-like chunks
            - CHUNKS when docs are paragraph-like / larger chunks

    Raises
    ------
    ValueError:
        If `source_kind` is unknown or no documents were produced.
    """
    match source_kind:
        case SourceKind.TEXT:
            docs = extract_txt_sentences(path)
            mode = DecomposeMode.SENTENCES

        # case SourceKind.PDF_SENTENCES:
        #     docs = extract_pdf_sentences(path)
        #     mode = DecomposeMode.SENTENCES

        case SourceKind.PDF_CHUNKS:
            docs = extract_pdf_chunks(path)
            mode = DecomposeMode.CHUNKS

        case _:
            raise ValueError(f"Unknown SourceKind: {source_kind!r}")

    if not docs:
        raise ValueError(f"No documents produced for source_kind={source_kind!r} path={path!r}")
    
    save_chunked_documents_json(docs=docs, source_kind=source_kind)

    return docs, mode
