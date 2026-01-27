# from __future__ import annotations

# import logging
# import os
# import re
# from dataclasses import dataclass
# from pathlib import Path
# from typing import Iterable, List, Optional, Tuple

# import fitz  # PyMuPDF
# import spacy # type: ignore[import]
# from kbdebugger.compat.langchain import Document

# logger = logging.getLogger(__name__)

# # ---------------------------------------------------------------------------
# # SpaCy model (loaded once)
# # ---------------------------------------------------------------------------
# try:
#     _NLP = spacy.load("en_core_web_sm")
# except OSError as exc:
#     raise RuntimeError(
#         "SpaCy model 'en_core_web_sm' is not installed. "
#         "Install it via:\n\n"
#         "    python -m spacy download en_core_web_sm\n"
#     ) from exc


# # ---------------------------------------------------------------------------
# # Data structures
# # ---------------------------------------------------------------------------
# @dataclass(frozen=True)
# class RawPage:
#     """Raw text extracted from a single PDF page."""
#     page_number: int  # 1-indexed
#     text: str


# @dataclass(frozen=True)
# class CleanedPage:
#     """Page text after applying cleaning and filtering rules."""
#     page_number: int
#     cleaned_text: str


# @dataclass(frozen=True)
# class SentencePage:
#     """A page represented as a list of sentences."""
#     page_number: int
#     sentences: List[str]


# # ---------------------------------------------------------------------------
# # Pipeline stages
# # ---------------------------------------------------------------------------
# def load_pdf_pages(
#     pdf_path: str | Path,
#     page_limit: Optional[int] = None,
# ) -> Tuple[str, List[RawPage]]:
#     """
#     Load a PDF and extract raw text for each page.

#     Parameters
#     ----------
#     pdf_path:
#         Path to the PDF file.
#     page_limit:
#         Optional maximum number of pages to process.

#     Returns
#     -------
#     title:
#         Base filename (without extension), used as a document title/source.
#     pages:
#         List of RawPage objects, one per processed page.
#     """
#     pdf_path = Path(pdf_path)

#     try:
#         with fitz.open(pdf_path) as pdf:
#             logger.info("Opened PDF: %s", pdf_path)

#             filename = pdf_path.name
#             title, _ = os.path.splitext(filename)

#             num_pages = len(pdf)
#             if page_limit is not None:
#                 num_pages = min(num_pages, page_limit)

#             pages: List[RawPage] = []
#             for page_index in range(num_pages):
#                 page = pdf.load_page(page_index)
#                 text = page.get_text("text").strip()
#                 pages.append(RawPage(page_number=page_index + 1, text=text))

#         return title, pages

#     except Exception as exc:  # noqa: BLE001
#         logger.error("Error extracting text from %s: %s", pdf_path, exc)
#         # Preserve old behaviour: return empty result on failure
#         return "Untitled Document", []


# def clean_page_text(pages: Iterable[RawPage]) -> List[CleanedPage]:
#     """
#     Apply heuristic cleaning rules to each page's text.

#     Removes:
#     - DOIs
#     - lines starting with numbers like '1.' or '2:'
#     - email addresses
#     - common boilerplate words (Received, Abstract, Keywords, etc.)
#     - standalone page numbers

#     Also:
#     - fixes hyphenated line breaks ('retrieval-\\n augmented' → 'retrievalaugmented')
#     - collapses multiple whitespace characters into a single space
#     """
#     cleaned_pages: List[CleanedPage] = []

#     for page in pages:
#         lines = page.text.split("\n")
#         cleaned_lines: List[str] = []

#         for line in lines:
#             # Skip lines with DOIs
#             if re.search(r"doi:\s*\d+\.\d+/\S+", line, re.IGNORECASE):
#                 continue

#             # Skip lines starting with numbers followed by ':' or '.'
#             if re.match(r"^\d+[:.]", line):
#                 continue

#             # Skip lines containing email addresses
#             if re.search(
#                 r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
#                 line,
#             ):
#                 continue

#             # # Skip typical metadata / boilerplate lines
#             # if re.search(
#             #     r"(Received|revised|accepted|Keywords|Abstract)",
#             #     line,
#             #     re.IGNORECASE,
#             # ):
#             #     continue

#             # # Skip lines that are standalone numbers (e.g. page numbers)
#             # if re.match(r"^\d+$", line.strip()):
#             #     continue

#             # Fix hyphenated line breaks
#             line = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", line)

#             # Replace multiple spaces with a single space
#             line = re.sub(r"\s+", " ", line)

#             cleaned = line.strip()
#             if cleaned:
#                 cleaned_lines.append(cleaned)

#         cleaned_text = "\n".join(cleaned_lines)
#         cleaned_pages.append(
#             CleanedPage(page_number=page.page_number, cleaned_text=cleaned_text)
#         )

#     return cleaned_pages


# def split_into_sentences(
#     cleaned_pages: Iterable[CleanedPage],
#     min_length: int = 20,
# ) -> List[SentencePage]:
#     """
#     Use SpaCy to segment each cleaned page into sentences.

#     Parameters
#     ----------
#     cleaned_pages:
#         Iterable of cleaned page objects.
#     min_length:
#         Minimum sentence length (in characters) to keep.

#     Returns
#     -------
#     List[SentencePage]
#     """
#     sentence_pages: List[SentencePage] = []

#     for page in cleaned_pages:
#         doc = _NLP(page.cleaned_text)
#         sentences = [
#             sent.text.strip()
#             for sent in doc.sents
#             if len(sent.text.strip()) > min_length
#         ]

#         sentence_pages.append(
#             SentencePage(page_number=page.page_number, sentences=sentences)
#         )

#     return sentence_pages


# def sentences_to_documents(
#     sentence_pages: Iterable[SentencePage],
#     source_title: str,
#     pdf_path: str | Path | None = None,
# ) -> List[Document]:
#     """
#     Convert sentence pages into LangChain Document objects.

#     Each sentence becomes one Document with metadata:
#     - page_number
#     - sentence_index (0-based within page)
#     - source (e.g. PDF title)
#     - pdf_path (optional, if provided)
#     """
#     documents: List[Document] = []
#     pdf_path_str = str(pdf_path) if pdf_path is not None else None

#     for page in sentence_pages:
#         for idx, sentence in enumerate(page.sentences):
#             metadata = {
#                 "page_number": page.page_number,
#                 "sentence_index": idx,
#                 "source": source_title,
#             }
#             if pdf_path_str is not None:
#                 metadata["pdf_path"] = pdf_path_str

#             documents.append(
#                 Document(
#                     page_content=sentence,
#                     metadata=metadata,
#                 )
#             )

#     return documents


# # ---------------------------------------------------------------------------
# # Public high-level API
# # ---------------------------------------------------------------------------
# def extract_pdf_sentences(
#     pdf_path: str | Path,
#     page_limit: Optional[int] = None,
#     min_sentence_length: int = 20,
# ) -> List[Document]:
#     """
#     High-level pipeline: PDF → sentence-level LangChain Documents.

#     Parameters
#     ----------
#     pdf_path:
#         Path to the input PDF file.
#     page_limit:
#         Optional maximum number of pages to process.
#     min_sentence_length:
#         Minimum sentence length (in characters) to keep.

#     Returns
#     -------
#     List[Document]
#         One Document per accepted sentence, with useful metadata.
#     """
#     pdf_path = Path(pdf_path)

#     title, raw_pages = load_pdf_pages(pdf_path, page_limit=page_limit)
#     if not raw_pages:
#         logger.warning("No text extracted from PDF: %s", pdf_path)
#         return []

#     cleaned_pages = clean_page_text(raw_pages)
#     sentence_pages = split_into_sentences(
#         cleaned_pages, min_length=min_sentence_length
#     )
#     return sentences_to_documents(
#         sentence_pages,
#         source_title=title,
#         pdf_path=pdf_path,
#     )


# __all__ = [
#     "RawPage",
#     "CleanedPage",
#     "SentencePage",
#     "load_pdf_pages",
#     "clean_page_text",
#     "split_into_sentences",
#     "sentences_to_documents",
#     "extract_pdf_sentences",
# ]
