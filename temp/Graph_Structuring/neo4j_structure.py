# from langchain_neo4j import Neo4jGraph
from typing import Any, List, Optional
# from langchain_community.graphs import Neo4jGraph
from dotenv import load_dotenv
import os
from .clients import connect_graph_client
from core.types import EdgeProperties, ExtractionResult, GraphEdge, GraphRelation
from langchain_core.documents import Document
from datetime import datetime, timezone

# load the environment variables
load_dotenv(override=True)

# Set up connection to graph instance using LangChain
# kg = Neo4jGraph(
#     url=os.getenv("NEO4J_URI"),
#     username=os.getenv("NEO4J_USERNAME","neo4j"),
#     password=os.getenv("NEO4J_PASSWORD","")
# )

graph_client = connect_graph_client()

print(f"[TrustifAI] Connected to Neo4j at {os.getenv('NEO4J_URI')} as user '{os.getenv('NEO4J_USERNAME','neo4j')}'")

def _normalize_label(text: str) -> str:
    """
    Normalize a free-text label into a safe identifier:
    - lowercase
    - collapse spaces -> underscores
    - strip punctuation at edges
    """
    clean = " ".join(text.split()).strip().lower()
    clean = clean.replace(" ", "_")
    return clean

# -------------------------
# Public helpers
# -------------------------
def query_graph(query: str, params: Optional[dict[str, Any]] = None) -> list[dict[str, str]]:
    try:
        return graph_client.query(query, params=params or {})
    except Exception as e:
        # You can log here if you like
        raise RuntimeError(f"[query_graph] Query failed: {e}") from e

# def create_relations(edge_object, sentence_doc):
#     return [{
#         'source': {
#             'label': edge[0]
#         },
#         'target': {
#             'label': edge[1]
#         },
#         'edge': {
#             'label': edge[2],
#             'properties': {
#                 'sentence': edge_object["sentence"], # coming from the extraction result
#                 "original_sentence": sentence_doc.page_content, # coming from the original document
#                 **sentence_doc.metadata
#             }
#         },
#     } for edge in edge_object["edges"]]

def map_extracted_triplets_to_graph_relations(
    extraction: ExtractionResult,
    source_doc: Document,
    # *,
    # include_sentence: bool = True,
) -> List[GraphRelation]:
    """
    Map an ExtractionResult to graph-ready relation dicts.
    - extraction: {"sentence": str, "edges": [(subj,obj,rel), ...]}
    - source_doc: LangChain Document (for provenance: page_content + metadata)
    """
    # defensive: accept partially-typed dicts
    sentence_text = extraction.get("sentence")
    triplets = extraction.get("triplets", [])

    rels: List[GraphRelation] = []
    for subj, obj, rel in triplets:
        # normalize labels to snake_case-ish and trim
        # s_label = _normalize_label(subj)
        # t_label = _normalize_label(obj)
        # e_label = _normalize_label(rel)

        props: EdgeProperties = {
            # for provenance
            'sentence': sentence_text,
            'original_sentence': getattr(source_doc, "page_content", ""),
            **getattr(source_doc, "metadata", {})  # type: ignore[arg-type]
        }
        # if include_sentence:
        #     # human-readable extracted sentence (from the extractor)
        #     props["sentence"] = sentence_text

        rels.append({
            "source": { "label": subj },
            "target": { "label": obj },
            "edge":   { "label": rel, "properties": props },
        })

    return rels

def upsert_graph_relation(relation: GraphRelation) -> list[dict[str, Any]]:
    # relation = {
    #     'source': {
    #         'label': 'Monitoring'
    #     },
    #     'target': {
    #         'label': 'KI system'
    #     },
    #     'edge': {
    #         'label': 'is performed during operation of',
    #         'properties': {
    #             'sentence': 'Monitoring is performed during operation of KI system',
    #             'source': '20241015_MISSION_KI_Glossar_v1.0 en.pdf',
    #             'page_number': 1,
    #             'start_index': 0
    #         }
    #     },
    # }
    
    src_label = relation['source']['label']     # e.g., 'Monitoring'
    tgt_label = relation['target']['label']     # e.g., 'KI system'
    rel_label = relation['edge']['label']       # e.g., 'is performed during operation of'
    props_all = relation['edge']['properties']  # sentence/source/page/etc
    
    # Minimal key (choose your policy):
    #   Option A (one edge per label between same nodes):
    # key_props = {"label": rel_label}
    #
    #   Option B (dedupe per sentence-location):
    rel_key_props: EdgeProperties = {
        "label": rel_label,
        "source": props_all.get("source", ""), 
        # "page_number": props_all.get("page_number", 0),
        # "start_index": props_all.get("start_index", 0),
        # "end_index": props_all.get("end_index", 0),
    }
    # ⚠️ remember: the rel_key_props are the props of the relationship used to find existing rels!
    # so choose them carefully to avoid over- or under-merging.

    # on create: keep every useful bit + created_at
    on_create_props = {
        **props_all, # we want to store metadata but not match on it
        # "created_at": __import__("time").time(),
        "created_at": datetime.now(timezone.utc).isoformat(),  # "2025-11-06T12:03:45.678+00:00",
    }
    
    # on match: only mutable audit fields
    on_match_props = {
        # "last_updated_at": __import__("time").time(),
        "last_updated_at": datetime.now(timezone.utc).isoformat(),
    }    
    
    """
    apoc.merge.relationship is a Neo4j APOC procedure used to dynamically merge or create a relationship between two nodes, which either exists or is created based on the provided parameters. 
    It handles dynamic relationship types and properties for creation or matching, and its signature is apoc.merge.relationship(
        startNode, 
        relType,        # e.g., "REL"
        relKeyProps,    # properties used to identify existing relationships
        onCREATEProps,  # properties set only when a new relationship is created
        endNode, 
        onMatchProps    # properties updated when a relationship already exists
    ). 
    This is useful for building Cypher queries where the relationship details are provided as parameters, for example, when unwinding a list of rows.
    """
    
    # About {} vs {{}}
    # - In a plain triple-quoted Python string (""" ... """), {} is just literal braces — fine.
    # - In an f-string (f""" ... """), {} is interpolation. To emit literal braces, you must escape as {{}}.
    # So:
    # - If you keep it as a plain string: """ ... {} ... """ is OK.
    # - If you switch to f""" ... """: change to {{}}.
    
    query_result = graph_client.query(
        """
        MERGE (s:Node {label: $source_label})
        ON CREATE SET s.created_at = datetime()
        SET s.last_updated_at = datetime(),
            s.created_at = coalesce(s.created_at, datetime())
        
        MERGE (t:Node {label: $target_label})
        ON CREATE SET t.created_at = datetime()
        SET t.last_updated_at = datetime(),
            t.created_at = coalesce(t.created_at, datetime())

        WITH s,t
        CALL apoc.merge.relationship(
            s,
            $rel_type, 
            $rel_key_props, 
            $on_create,
            t,
            $on_match
        ) YIELD rel
        
        // ensure temporal props exist on the rel too
        SET rel.created_at     = coalesce(rel.created_at, datetime()),
        rel.last_updated_at = datetime()
    
        RETURN s,t,rel
        """,
        params={
          'source_label': src_label,
          'target_label': tgt_label,
          'rel_type': 'REL', # always 'REL' as the relationship type; actual label is in properties
          'rel_key_props': rel_key_props,
          'on_create': on_create_props, # set only on create
          'on_match': on_match_props,   # set only on match (update)
        }
    )
    
    # Why this is safer
    # - Option A: We won't create a new rel just because page_number or some metadata changed.
    # - We still persist all the rich properties on first create, and can update on matches.

    return query_result
