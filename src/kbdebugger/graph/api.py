from __future__ import annotations

from typing import List

from .retriever import KnowledgeGraphRetriever
from kbdebugger.types import GraphRelation


def retrieve_keyword_subgraph(
    *,
    keyword: str,
    limit_per_pattern: int,
) -> List[GraphRelation]:
    """
    Retrieve a keyword-guided KG subgraph from Neo4j and return its relations.

    This function is a **public stage API**: it performs the retrieval and
    enforces a clear contract for downstream stages.

    Parameters
    ----------
    keyword:
        Keyword used to drive the subgraph retrieval patterns.

    limit_per_pattern:
        Maximum number of relations returned per retrieval pattern in the
        KnowledgeGraphRetriever.

    Returns
    -------
    List[GraphRelation]
        The retrieved relations (GraphRelation dicts), ready to be used as the
        reference set for vector similarity filtering.

    Raises
    ------
    ValueError
        If no relations were retrieved. This typically indicates that:
        - the keyword does not exist in the KG (or is too specific),
        - the KG is empty,
        - the retriever patterns are too restrictive,
        - or Neo4j connectivity/configuration is wrong.
    """
    retriever = KnowledgeGraphRetriever(limit_per_pattern=limit_per_pattern)
    hits = retriever.retrieve(keyword)
    relations = [h["relation"] for h in hits]

    if not relations:
        raise ValueError(
            "KG retrieval returned no relations. "
            f"keyword={keyword!r}, limit_per_pattern={limit_per_pattern}. "
            "Try a different keyword or verify the KG contains relevant nodes/edges."
        )

    return relations