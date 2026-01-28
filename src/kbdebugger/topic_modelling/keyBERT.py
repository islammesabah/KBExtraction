from __future__ import annotations

from typing import List, Literal, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from unittest import result

import rich

from keybert import KeyBERT
from sentence_transformers import SentenceTransformer, util as sbert_util
from kbdebugger.utils.json import now_utc_compact, write_json


MatchType = Literal[
    "exact",
    "synonym",
    "near_paragraph_global",
    "near_paragraph_keywords"
]

@dataclass(frozen=True)
class ParagraphMatch:
    index: int
    paragraph: str
    keywords: List[str]
    match_type: Optional[MatchType]
    matched_terms: List[str]
    embedding_model_name: str
    score: Optional[float] = None


@dataclass(frozen=True)
class KeyBERTConfig:
    embedding_model: str = "all-mpnet-base-v2"
    # embedding_model: str = "all-MiniLM-L6-v2"

    ngram_range: Tuple[int, int] = (1, 1)
    # To extract keyphrases, simply set keyphrase_ngram_range to (1, 2) or higher 
    # depending on the number of words you would like in the resulting keyphrases.

    top_n: int = 8 # top_n keywords to be extracted by paragraph

    search_kw_to_paragraph_similarity_threshold: float = 0.45  # Fallback semantic similarity (paragraph vs keyword)
    search_kw_to_keywords_similarity_threshold: float = 0.65



def run_keybert_matching(
    paragraphs: List[str],
    search_keyword: str,
    synonyms: Optional[List[str]] = None,
    config: Optional[KeyBERTConfig] = None
) -> Tuple[
        List[ParagraphMatch],
        List[ParagraphMatch]
    ]:
    """
    Extract keywords from paragraphs using KeyBERT and match them to a target keyword.
    Includes exact match, synonym match, and two levels of semantic similarity fallbacks.



    Parameters
    ----------
    paragraphs: List[str]
        The input text blocks (e.g., from Docling).
    
    keyword: str
        The concept of interest (e.g., "explainability").
    
    embedding_model_name: str
        SentenceTransformer model used for both KeyBERT and fallback similarity.
    
    top_n: int
        How many keywords to extract per paragraph.
    
    similarity_threshold: float
        Cosine similarity threshold for semantic fallback.

    Returns
    -------
    separate lists for matched and unmatched paragraphs.
    """
    cfg = config or KeyBERTConfig()
    synonyms = synonyms or []
    synonym_set = set(s.lower() for s in synonyms)
    search_keyword_lower = search_keyword.lower()

    sentence_model = SentenceTransformer(cfg.embedding_model)
    kw_model = KeyBERT(sentence_model)
    search_keyword_embedding = sentence_model.encode(search_keyword, convert_to_tensor=True)

    matched: List[ParagraphMatch] = []
    unmatched: List[ParagraphMatch] = []

    for i, paragraph in enumerate(paragraphs):
        # Step 1: Extract top-n keywords from paragraph
        extracted_keywords = kw_model.extract_keywords(
            paragraph,
            keyphrase_ngram_range=cfg.ngram_range,
            stop_words="english",
            top_n=cfg.top_n,
        )
        paragraph_keywords = [kw for kw, _probs in extracted_keywords]
        paragraph_keywords_lower = [kp.lower() for kp in paragraph_keywords]

        # Step 2: Match logic
        match_type: Optional[MatchType] = None
        matched_terms: List[str] = []

        matched_synonyms = synonym_set.intersection(paragraph_keywords_lower) # only needed if failed to "exact" match
        score: Optional[float] = None # only needed for semantic similarity (fallback)

        if search_keyword_lower in paragraph_keywords_lower:
            match_type = "exact"
            matched_terms = [search_keyword_lower]
        elif matched_synonyms:
            match_type = "synonym"
            matched_terms = list(matched_synonyms)
        else:
            # Step 3: Fallback to semantic similarity

            # Fallback 1: Cosine similarity with paragraph as a whole
            paragraph_embedding = sentence_model.encode(paragraph, convert_to_tensor=True)
            similarity_score = float(
                sbert_util.cos_sim(
                    search_keyword_embedding, 
                    paragraph_embedding
                )
                .item()
            ) 
            # similaroty_score is a 1x1 tensor -- a matrix with a single cosine similarity value
            # .item() extracts the scalar value from a tensor (e.g., tensor([[0.4632]]) → 0.4632)
            if similarity_score >= cfg.search_kw_to_paragraph_similarity_threshold:
                match_type = "near_paragraph_global"
                score = similarity_score
            else:
                # Fallback 2: Compare to each extracted keyword in this paragraph
                keyword_embeddings = sentence_model.encode(paragraph_keywords, convert_to_tensor=True)
                # - keyword_embeddings is a list of vectors, one for each extracted keyword.
                # - So if a paragraph has 8 keywords, then this will be a tensor of shape: [8, embedding_dim].
                sim_scores = sbert_util.cos_sim(
                    search_keyword_embedding, 
                    keyword_embeddings
                )[0]
                # - This is comparing a single vector (1 × dim) vs. a matrix (8 × dim).
                # - The result will be a 1×8 matrix: cosine similarity of the keyword with each of the 8 keywords.

                # 🧾 What does [0] do?
                # - It removes the first dimension ([1, N] → [N]) to give you a flat list of scores.
                # - Now sim_scores is a 1D tensor with N values (one per keyword).
                
                # We want the most semantically similar keyword match, so we take the highest similarity value.
                max_score = float(sim_scores.max().item())
                if max_score >= cfg.search_kw_to_keywords_similarity_threshold:
                    match_type = "near_paragraph_keywords"
                    score = max_score


        record = ParagraphMatch(
            index=i,
            paragraph=paragraph,
            keywords=paragraph_keywords,
            match_type=match_type,
            matched_terms=matched_terms,
            score=score,
            embedding_model_name=cfg.embedding_model,
        )

        if match_type:
            matched.append(record)
        else:
            unmatched.append(record)

    save_keybert_matched_paragrahs(
        matched=matched,
        unmatched=unmatched,
        keyword=search_keyword,
        synonyms=synonyms
    )

    return matched, unmatched


def save_keybert_matched_paragrahs(
        *,
        matched: List[ParagraphMatch],
        unmatched: List[ParagraphMatch],
        keyword: str,
        synonyms: Optional[List[str]] = None,
        output_dir: str = "logs"
) -> None:
    """
    Save full KeyBERT paragraph match results including matched and unmatched paragraphs.
    """
    timestamp = now_utc_compact()
    payload: Dict[str, Any] = {
        "created_at": timestamp,
        "keyword": keyword,
        "generated_synonyms": synonyms or [],
        "num_matched": len(matched),
        "num_unmatched": len(unmatched),
        "matched": [m.__dict__ for m in matched],
        "unmatched": [u.__dict__ for u in unmatched],
    }

    out_path = f"{output_dir}/01.1.6_keybert_paragraph_matched_paragraphs_{keyword}_{timestamp}.json"
    write_json(out_path, payload)
    rich.print(f"[INFO] Saved KeyBERT paragraph match matched_paragrahs to {out_path}")
