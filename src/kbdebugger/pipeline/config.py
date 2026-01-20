from __future__ import annotations

import os
from dataclasses import dataclass
from typing import cast

from kbdebugger.extraction.types import SourceKind
from kbdebugger.vector.api import VectorSimilarityFilterConfig


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """
    Central runtime configuration for the end-to-end KBDebugger pipeline.

    This config is intentionally:
    - **explicit** (field names describe *exactly* what they control),
    - **environment-driven** (easy to run experiments without code edits).

    Stages controlled by this config
    --------------------------------
    1) KG subgraph retrieval (Neo4j):
        - which keyword to retrieve around
        - how many relations to fetch per retrieval pattern

    2) Corpus ingestion + decomposition:
        - which source kind to read (TEXT / PDF_SENTENCES / PDF_CHUNKS)
        - which path is used for that source kind

    3) Vector similarity filter:
        - which SentenceTransformer encoder is used
        - similarity threshold and top-k neighbor retrieval per quality

    4) Novelty comparator (LLM):
        - decoding/length parameters for the novelty decision model

    5) Triplet extraction (LLM):
        - batch size for triplet extraction calls

    Environment variables
    ---------------------
    1️⃣ KG retrieval:
        KB_RETRIEVAL_KEYWORD:
            Keyword used to retrieve a KG subgraph from Neo4j.
            Default: "requirement"

        KB_LIMIT_PER_PATTERN:
            Number of relations retrieved per retriever pattern.
            Default: 50

    2️⃣ Corpus:
        KB_SOURCE_KIND:
            One of: "TEXT", "PDF_SENTENCES", "PDF_CHUNKS"
            Default: "TEXT"

        KB_TEXT_PATH:
            Path to corpus text file (when KB_SOURCE_KIND == "TEXT")
            Default: "data/DSA/DSA_knowledge.txt"

        KB_PDF_PATH:
            Path to corpus PDF file (when KB_SOURCE_KIND starts with "PDF_")
            Default: "data/SDS/InstructCIR.pdf"

    3️⃣ Vector similarity filtering:
        KB_ENCODER_MODEL_NAME:
            🤗 HuggingFace model id for the SentenceTransformer encoder used to embed
            both candidate qualities and KG relation sentences.
            Default: "sentence-transformers/all-MiniLM-L6-v2"

        KB_ENCODER_DEVICE:
            Optional device string (e.g., "cpu", "cuda", "cuda:0").
            Empty means "let the backend decide".
            Default: "" (auto)

        KB_NORMALIZE_EMBEDDINGS:
            Whether embeddings are L2-normalized (recommended for cosine similarity).
            Default: true

        KB_QUALITY_TO_KG_TOP_K:
            Number of nearest KG relations to retrieve per candidate quality.
            This determines:
              - how many neighbors are kept for context/logging
              - how max_score is computed (best neighbor similarity)
            Default: 5

        KB_MIN_SIMILARITY_THRESHOLD:
            Minimum cosine similarity required to keep a quality.
            Default: 0.55

    4️⃣ Novelty comparator (LLM):
        KB_NOVELTY_LLM_MAX_TOKENS:
            Max tokens for novelty decision response.
            Default: 700

        KB_NOVELTY_LLM_TEMPERATURE:
            Temperature for novelty decision model.
            Default: 0.0

    5️⃣ Triplet extraction:
        KB_TRIPLET_EXTRACTION_BATCH_SIZE:
            How many qualifying quality sentences to send in one triplet extraction call.
            Default: 5
    """
   # ----------------------------
    # KG retrieval
    # ----------------------------
    kg_retrieval_keyword: str
    kg_limit_per_pattern: int

    # ----------------------------
    # Corpus selection
    # ----------------------------
    source_kind: SourceKind
    corpus_path: str

    # ----------------------------
    # Vector similarity filter
    # ----------------------------
    vector_similarity: VectorSimilarityFilterConfig

    # ----------------------------
    # Novelty comparator (LLM)
    # ----------------------------
    novelty_llm_max_tokens: int
    novelty_llm_temperature: float

    # ----------------------------
    # Triplet extraction
    # ----------------------------
    triplet_extraction_batch_size: int


    @classmethod
    def from_env(cls) -> PipelineConfig:
        """
        Construct a PipelineConfig from environment variables.

        This method is the **single authoritative place** that defines:
        - supported environment variables
        - defaults
        - validation and normalization rules

        Validation / normalization rules
        --------------------------------
        - KB_SOURCE_KIND is validated strictly.
        - kg_limit_per_pattern and triplet_extraction_batch_size are clamped to >= 1.
        - quality_to_kg_top_k is clamped to >= 1 (inside VectorSimilarityFilterConfig).
        - Empty KB_ENCODER_DEVICE is treated as None (auto device).

        Returns
        -------
        PipelineConfig
            Fully populated pipeline configuration.

        Raises
        ------
        ValueError
            If KB_SOURCE_KIND is not one of the supported enum values.
        """
        # ---------- KG retrieval ----------
        kg_retrieval_keyword = os.getenv("KB_RETRIEVAL_KEYWORD", "requirement").strip()
        kg_limit_per_pattern = int(os.getenv("KB_LIMIT_PER_PATTERN", "50").strip())
        kg_limit_per_pattern = max(1, kg_limit_per_pattern)

        # ---------- Corpus ----------
        source_raw = os.getenv("KB_SOURCE_KIND", "TEXT").upper().strip()
        if source_raw not in {"TEXT", "PDF_SENTENCES", "PDF_CHUNKS"}:
            raise ValueError(f"Invalid KB_SOURCE_KIND={source_raw!r}")
        source_kind = cast(SourceKind, source_raw)

        text_path = os.getenv("KB_TEXT_PATH", "data/DSA/DSA_knowledge.txt").strip()
        pdf_path = os.getenv("KB_PDF_PATH", "data/SDS/InstructCIR.pdf").strip()

        corpus_path = text_path if source_kind == SourceKind.TEXT else pdf_path

        # ---------- Vector similarity ----------
        encoder_model_name = os.getenv(
            "KB_ENCODER_MODEL_NAME",
            "sentence-transformers/all-MiniLM-L6-v2",
        ).strip()

        encoder_device_raw = os.getenv("KB_ENCODER_DEVICE", "").strip()
        encoder_device = encoder_device_raw or None

        normalize_embeddings = os.getenv("KB_NORMALIZE_EMBEDDINGS", "true").strip().lower() in {
            "1",
            "true",
            "yes",
        }

        quality_to_kg_top_k = int(os.getenv("KB_QUALITY_TO_KG_TOP_K", "5").strip())
        quality_to_kg_top_k = max(1, quality_to_kg_top_k)

        min_similarity_threshold = float(os.getenv("KB_MIN_SIMILARITY_THRESHOLD", "0.55").strip())

        vector_similarity = VectorSimilarityFilterConfig(
            encoder_model_name=encoder_model_name,
            encoder_device=encoder_device,
            normalize_embeddings=normalize_embeddings,
            quality_to_kg_top_k=quality_to_kg_top_k,
            min_similarity_threshold=min_similarity_threshold,
        )

        # ---------- Novelty comparator ----------
        novelty_llm_max_tokens = int(os.getenv("KB_NOVELTY_LLM_MAX_TOKENS", "700").strip())
        novelty_llm_temperature = float(os.getenv("KB_NOVELTY_LLM_TEMPERATURE", "0.0").strip())


        # ---------- Triplet extraction ----------
        triplet_extraction_batch_size = int(os.getenv("KB_TRIPLET_EXTRACTION_BATCH_SIZE", "5").strip())
        triplet_extraction_batch_size = max(1, triplet_extraction_batch_size)


        return cls(
            kg_retrieval_keyword=kg_retrieval_keyword,
            kg_limit_per_pattern=kg_limit_per_pattern,

            source_kind=source_kind,
            corpus_path=corpus_path,

            vector_similarity=vector_similarity,
            
            novelty_llm_max_tokens=novelty_llm_max_tokens,
            novelty_llm_temperature=novelty_llm_temperature,
            
            triplet_extraction_batch_size=triplet_extraction_batch_size,
        )
