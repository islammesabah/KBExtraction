from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from pydoc_data import topics
from typing import List, Optional, Tuple, Literal, TypedDict

from bertopic import BERTopic

from sklearn.feature_extraction.text import CountVectorizer
from .logging import save_topic_modeling_results


@dataclass(frozen=True)
class TopicModelConfig:
    """
    Configuration for topic modeling with BERTopic.

    Parameters
    ----------
    embedding_model: str or model
        The sentence transformer or embedding model used to vectorize texts.

    min_topic_size: int
        Minimum size of a topic. Used by HDBSCAN to avoid very small, noisy clusters.

    top_n_words: int
        Number of representative keywords to extract per topic.

    language: str
        Language used by CountVectorizer for stopword removal.

    seed: int
        Random seed for reproducibility.
    """
    # embedding_model: str = "all-MiniLM-L6-v2" # dimension: 384
    embedding_model: str = "all-mpnet-base-v2" # dimension: 768
    min_topic_size: int = 10
    top_n_words: int = 16
    language: str = "english"
    seed: int = 42


class TopicResult(TypedDict):
    topic_id: int
    keyword_frequency: float
    keywords: List[str]
    paragraph_indices: List[int]
    matched: Literal["exact", "synonym", "none"]


def extract_topics_from_paragraphs(
    paragraphs: List[str],
    keyword: str,
    synonyms: Optional[List[str]] = None,
    config: Optional[TopicModelConfig] = None,
) -> Tuple[
        List[TopicResult], 
        BERTopic
    ]:
    """
    Run BERTopic over the provided paragraphs and detect topics matching a given keyword.

    Parameters
    ----------
    paragraphs:
        List of clean paragraph strings to analyze.

    keyword:
        The user-selected topic of interest (e.g., "explainability").

    synonyms:
        Optional backup list of synonyms (used if exact keyword fails).

    config:
        Topic modeling hyperparameters. Defaults to sensible values.

    Returns
    -------
    - topic_matches: List of topic match metadata (see TopicResult).
    - model: Trained BERTopic model for further inspection/plotting.
    """
    cfg = config or TopicModelConfig()

    # Step 1: Instantiate BERTopic with configuration

    # Custom vectorizer with stopword removal
    vectorizer_model = CountVectorizer(stop_words=cfg.language)
    topic_model = BERTopic(
        embedding_model=cfg.embedding_model,
        vectorizer_model=vectorizer_model,
        top_n_words=cfg.top_n_words,
        language=cfg.language,
        calculate_probabilities=True,
        verbose=True,
        seed_topic_list=None,
    )

    # Step 2: Fit the model to input paragraphs
    topics, _probs = topic_model.fit_transform(paragraphs)
    # topics is List[int] of topic IDs per paragraph
    # propbs is List[List[float]] of topic probabilities per paragraph

    # cast the topics to a list of ints
    topics = list(map(int, topics))

    # Access the frequent topics that were generated:
    topic_info_df = topic_model.get_topic_info()
    # e.g.
    """
    >>> topic_info_df
    Topic   Count   Name
    -1      4630    -1_can_your_will_any
    0       693     49_windows_drive_dos_file
    1       466     32_jesus_bible_christian_faith
    2       441     2_space_launch_orbit_lunar
    3       381     22_key_encryption_keys_encrypted
    ...
    """

    # Step 3: Collect match info for all topics
    topic_matches: List[TopicResult] = []
    keyword_lower = keyword.lower()
    synonym_set = set(s.lower() for s in synonyms) if synonyms else set()

    matched_topic_ids: List[int] = [] # e.g. [3, 7]
    matched_synonyms: dict[int, set[str]] = {} # e.g. {7: {"explainable AI"}}
    match_type_by_topic: dict[int, str] = {} # e.g. {3: "exact", 7: "synonym"}


    for topic_id in topic_info_df["Topic"]:
        if topic_id == -1:
            # -1 is outlier cluster in HDBSCAN
            # Topic -1 refers to all outliers and should typically be ignored.
            continue

        # Get topic keywords and lowercased form for matching
        """
        >>> topic_model.get_topic(topic_id) # topic_id is an int
        BERTopic’s get_topic method returns the top-N highest TF-IDF keywords per topic.

        [('windows', 0.006152228076250982),
        ('drive', 0.004982897610645755),
        ('dos', 0.004845038866360651),
        ('file', 0.004140142872194834),
        ('disk', 0.004131678774810884),
        ('mac', 0.003624848635985097),
        ('memory', 0.0034840976976789903),
        ('software', 0.0034415334250699077),
        ('email', 0.0034239554442333257),
        ('pc', 0.003047105930670237)]
        """
        topic_words = [w for w, w_prob in topic_model.get_topic(topic_id)]
        topic_words_lower = [w.lower() for w in topic_words]

        match_type: Literal["exact", "synonym", "none"]
        # Matching logic
        if keyword_lower in topic_words_lower:
            # 💪 The user-chosen keyword was mentioned in the topic's keywords list
            match_type = "exact"
            matched_topic_ids.append(topic_id)
        else:
            # The exact keyword was not found, check synonyms if available
            intersecting = synonym_set.intersection(topic_words_lower)
            if intersecting:
                match_type = "synonym"
                matched_topic_ids.append(topic_id)
                # matched_synonyms[topic_id] = list(intersecting)[0] # store one matched synonym
                matched_synonyms[topic_id] = intersecting
            else:
                continue # skip the topic if no match

        match_type_by_topic[topic_id] = match_type

        # Find all paragraphs belonging to this topic
        paragraph_indices = [i for i, t in enumerate(topics) if t == topic_id]

        # Compute how often the user keyword appears in the topic's top keywords.
        # Usually 0 or 1, since BERTopic keywords are typically unique, but may repeat in rare cases.
        keyword_frequency = topic_words_lower.count(keyword_lower)

        topic_matches.append(
            TopicResult(
                topic_id=topic_id,
                keyword_frequency=keyword_frequency,
                keywords=topic_words,
                paragraph_indices=paragraph_indices,
                matched=match_type,
            )
        )

    # # Using .get_document_info, we can also extract information on a document level, 
    # # such as their corresponding topics, probabilities, whether they are representative documents for a topic, etc.   
    # """
    # >>> topic_model.get_document_info(docs)

    # Document                               Topic    Name                        Top_n_words                     Probability    ...
    # I am sure some bashers of Pens...       0       0_game_team_games_season    game - team - games...          0.200010       ...
    # My brother is in the market for...      -1     -1_can_your_will_any         can - your - will...            0.420668       ...
    # Finally you said what you dream...      -1     -1_can_your_will_any         can - your - will...            0.807259       ...
    # Think! It is the SCSI card doing...     49     49_windows_drive_dos_file    windows - drive - docs...       0.071746       ...
    # 1) I have an old Jasmine drive...       49     49_windows_drive_dos_file    windows - drive - docs...       0.038983       ...
    # """
    # topic_model.get_topic_info()

    # Save logs for this topic modeling run
    save_topic_modeling_results(
        topic_model=topic_model,
        documents=paragraphs,
        # document_chunks=...,
        keyword=keyword,
        matched_topic_ids=matched_topic_ids,
        match_type_by_topic=match_type_by_topic,
        matched_synonyms=matched_synonyms,
        generated_synonyms=synonyms,
    )

    return topic_matches, topic_model
