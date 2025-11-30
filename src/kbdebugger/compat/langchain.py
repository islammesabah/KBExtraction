"""
Compatibility shims for LangChain imports.

Usage in our code:
    from kbdebugger.compat.langchain import Document, PromptTemplate, Runnable, BaseRetriever
"""
from __future__ import annotations
from typing import Any

# --- Document ---------------------------------------------------------------
# Declare the name up-front so Pylance knows it exists.
Document: Any
try:
    # Newer public path in some releases
    from langchain.schema import Document as _Doc  # type: ignore
except Exception:
    try:
        # LangChain 1.0.x
        from langchain_core.documents import Document as _Doc  # type: ignore
    except Exception:  # legacy fallback
        from langchain.docstore.document import Document as _Doc  # type: ignore
Document = _Doc

# --- PromptTemplate ---------------------------------------------------------
PromptTemplate: Any
try:
    from langchain.prompts import PromptTemplate as _PT # type: ignore
except Exception:
    from langchain_core.prompts.prompt import PromptTemplate as _PT  # type: ignore
PromptTemplate = _PT

# --- Runnable ---------------------------------------------------------------
try:
    from langchain.schema.runnable import Runnable  # type: ignore
except Exception:
    try:
        from langchain_core.runnables import Runnable  # type: ignore
    except Exception:
        # Optional: define a minimal Protocol as a last-resort fallback
        from typing import Protocol, Any
        class Runnable(Protocol):  # type: ignore
            def invoke(self, input: Any, **kwargs: Any) -> Any: ...

# ------------------ Retrievers ------------------
EnsembleRetriever: Any
BM25Retriever: Any

# --- BaseRetriever (commonly used) -----------------------------------------
BaseRetriever: Any
try:
    from langchain_core.retrievers import BaseRetriever  # type: ignore
except Exception:
    from langchain.retrievers import BaseRetriever  # type: ignore

from langchain_community.retrievers import BM25Retriever # type: ignore

# --- Ensemble ---
try:
    # some versions export it here
    from langchain_community.retrievers import EnsembleRetriever as _Ens # type: ignore
    EnsembleRetriever = _Ens
except Exception:
    try:
        # reliable community submodule path
        from langchain_community.retrievers.ensemble import EnsembleRetriever as _Ens # type: ignore
        EnsembleRetriever = _Ens
    except Exception:
        try:
            # newer split (if/when present)
            from langchain.retrievers.ensemble import EnsembleRetriever as _Ens # type: ignore
            EnsembleRetriever = _Ens
        except Exception:
            EnsembleRetriever = None  # type: ignore

from langchain_huggingface import HuggingFaceEmbeddings # type: ignore
from langchain_chroma import Chroma # type: ignore

from langchain_text_splitters import RecursiveCharacterTextSplitter # type: ignore

# ------------------ PDF Loaders ------------------
# Prefer PyMuPDF (fast, you already have pymupdf). Fallback to Unstructured if available.
PyMuPDFLoader: Any
try:
    from langchain_community.document_loaders import PyMuPDFLoader as _PyMuPDFLoader # type: ignore
    PyMuPDFLoader = _PyMuPDFLoader
except Exception:
    PyMuPDFLoader = None  # type: ignore

# UnstructuredPDFLoader: Any
# try:
#     from langchain_community.document_loaders import UnstructuredPDFLoader as _UnstructuredPDFLoader # type: ignore
#     UnstructuredPDFLoader = _UnstructuredPDFLoader
# except Exception:
#     UnstructuredPDFLoader = None  # type: ignore

# UnstructuredPDFLoader: REQUIRED
UnstructuredPDFLoader: Any
try:
    from langchain_community.document_loaders import UnstructuredPDFLoader as _UnstructuredPDFLoader  # type: ignore
    UnstructuredPDFLoader = _UnstructuredPDFLoader
except Exception as exc:
    raise ImportError(
        "UnstructuredPDFLoader requires the 'unstructured' package.\n"
        "Install it with:\n\n"
        "    pip install unstructured unstructured-inference unstructured.pytesseract\n"
    ) from exc

# ------------------ Graphs (Neo4j) ------------------
from langchain_community.graphs import Neo4jGraph # type: ignore

__all__ = [
    "Document",
    "PromptTemplate",
    "Runnable",
    "BaseRetriever",
    "BM25Retriever",
    "EnsembleRetriever",
    "HuggingFaceEmbeddings",
    "Chroma",
    "RecursiveCharacterTextSplitter",
    "PyMuPDFLoader",
    "UnstructuredPDFLoader",
    "Neo4jGraph",
]
