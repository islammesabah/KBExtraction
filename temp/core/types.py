from __future__ import annotations
from typing import TypedDict, Any
from typing_extensions import Required, NotRequired

Subject = str
Predicate = str
Object = str

TripletSOP = tuple[Subject, Object, Predicate]  # (Subject, Object, Predicate)

class ExtractionResult(TypedDict):
    sentence: str
    triplets: list[TripletSOP]  # [["Subject", "Object", "Relation"], ...]

class GraphEnd(TypedDict):
    label: str

class GraphEdge(TypedDict):
    label: str
    properties: EdgeProperties

class EdgeProperties(TypedDict, total=False):
    # total=False: all fields are optional, then we enforce some as Required below
    """
    Canonical schema for a relationship's properties stored in Neo4j.
    We mark some keys Required for downstream logic, and allow extra keys.
    """
    # ------- Required (minimum we rely on) -------
    label: Required[str]                     # e.g., "is" when the sentence is: "AI is transformative"
    sentence: NotRequired[str]                  # human-readable sentence (from extractor or synthesized)
    predicate_text: NotRequired[str]            # original predicate text (before normalization)

    # ------- Strongly recommended provenance -------
    original_sentence: NotRequired[str]      # the raw text from the Document chunk
    source: NotRequired[str]            # e.g., PDF/file name
    page_number: NotRequired[int]
    start_index: NotRequired[int]
    end_index: NotRequired[int]
    doc_id: NotRequired[str]                 # internal ID of the doc/chunk
    chunk_id: NotRequired[str]               # if you chunked documents

    # ------- Quality / versioning -------
    confidence: NotRequired[float]           # model confidence if available
    extractor_version: NotRequired[str]      # version of your extraction pipeline
    created_at: NotRequired[str]             # ISO timestamp

    # ------- Open-ended for extra metadata -------
    # Any extra keys from sentence_doc.metadata are allowed
    # because TypedDict (total=False) + extra merge is permitted.

class GraphRelationWrite(TypedDict):
    """
    What we send to Neo4j to upsert a relationship.
    The relationship TYPE is the normalized predicate (or 'REL' if you use property-typed relations).
    """
    source_label: str
    target_label: str
    relationship_type: str     # e.g., "IS_SUBCLASS_OF" (Option A) or "REL" (Option B)
    properties: EdgeProperties

class GraphRelation(TypedDict):
    source: GraphEnd
    target: GraphEnd
    edge: GraphEdge

# class GraphRelation(TypedDict, total=False):
#     """Canonical edge shape for writing to Neo4j or logs."""
#     subject: str
#     object: str
#     relation: str
#     sentence: str  # optional human-readable source
#     metadata: dict[str, Any]
