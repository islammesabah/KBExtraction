from __future__ import annotations

from typing import List, Optional, Sequence

from kbdebugger.types import GraphRelation, ExtractionResult
from .retriever import KnowledgeGraphRetriever
from .utils import map_extracted_triplets_to_graph_relations
from .types import BatchUpsertSummary
from . import get_graph


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

    # if not relations:
    #     raise ValueError(
    #         "KG retrieval returned no relations. "
    #         f"keyword={keyword!r}, limit_per_pattern={limit_per_pattern}. "
    #         "Try a different keyword or verify the KG contains relevant nodes/edges."
    #     )

    return relations


def upsert_extracted_triplets(
    *,
    extractions: Sequence[ExtractionResult],
    source: Optional[str] = None,
    pretty_print: bool = True,
) -> BatchUpsertSummary:
    """
    Convert triplet extraction outputs into graph relations, then upsert them.

    Why this exists
    ---------------
    The triplet extractor returns "ExtractionResult" objects:
        {
          "sentence": str,
          "triplets": [(subject, object, predicate), ...]
        }

    Neo4j upsert expects GraphRelation objects:
        {
          "source": {"label": ...},
          "target": {"label": ...},
          "edge": {"label": ..., "properties": {...}}
        }

    This function is the stage boundary that:
    - maps ExtractionResult -> list[GraphRelation]
    - batches all relations together
    - performs a single high-level upsert call

    Parameters
    ----------
    graph:
        Connected GraphStore instance.

    extractions:
        Sequence of ExtractionResult items. Each item corresponds to one input sentence,
        containing zero or more extracted triplets.

    source:
        Optional provenance string (e.g., PDF filename). If provided, it is stored on
        relationship properties under key "source".

    pretty_print:
        If True, print an upsert summary.

    Returns
    -------
    BatchUpsertSummary
        Summary across all relations produced by all extractions.
    """
    graph = get_graph()
    all_relations: List[GraphRelation] = []

    for extraction in extractions:
        # extractions is like a list of list of triplets.
        # Thus, we have to iterate through each extraction (corresponding to one quality sentence) 
        # and map its triplets to graph relations. And we accumulate all triplets in one flat list to do a single upsert at the end.
        rels = map_extracted_triplets_to_graph_relations(extraction, source=source)
        all_relations.extend(rels)

    if not all_relations:
        # Nothing to upsert is not an error here; extraction may legitimately produce nothing.
        return BatchUpsertSummary(
            attempted=0,
            succeeded=0,
            failed=0,
            errors=[],
        )

    # Here we do a single batch upsert for all relations extracted from all sentences.
    # This is more efficient than upserting per `extraction`, and allows us to get a comprehensive summary of the batch operation.
    return graph.upsert_relations(all_relations, pretty_print=pretty_print)
