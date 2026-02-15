from kbdebugger.types import EdgeProperties, ExtractionResult, GraphRelation
from kbdebugger.compat.langchain import Document
from typing import List, Iterable, Mapping, Any, Optional
from datetime import datetime


def normalize_text(text: str) -> str:
    """
    Normalize a free-text label into a safe identifier:
    - lowercase
    - strip punctuation at edges
    """
    clean = " ".join(text.strip().split()).lower()
    # clean = clean.replace(" ", "_")
    return clean


def map_doc_extracted_triplets_to_graph_relations(
    extraction: ExtractionResult,
    source_doc: Document,
    # *,
    # include_sentence: bool = True,
) -> List[GraphRelation]:
    """
    Map an ExtractionResult to graph-ready relation dicts.
    - extraction: {"sentence": str, "triplets": [(subj,obj,rel), ...]}
    - source_doc: LangChain Document (for provenance: page_content + metadata)
    """
    # defensive: accept partially-typed dicts
    sentence_text = extraction.get("sentence")
    triplets = extraction.get("triplets", [])

    rels: List[GraphRelation] = []
    for subj, obj, rel in triplets:

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
            "source": { "label": normalize_text(subj) },
            "target": { "label": normalize_text(obj) },
            "edge":   { "label": normalize_text(rel), "properties": props },
        }) # type: ignore

    return rels


def map_extracted_triplets_to_graph_relations(
    extraction: ExtractionResult,
    source: Optional[str] = None,
) -> List[GraphRelation]:
    """
    Map an ExtractionResult to graph-ready relation dicts.
    - extraction: {"sentence": str, "triplets": [(subj,obj,rel), ...]}
    - source_doc: LangChain Document (for provenance: page_content + metadata)
    """
    # defensive: accept partially-typed dicts
    sentence_text = extraction.get("sentence")
    triplets = extraction.get("triplets", [])

    rels: List[GraphRelation] = []
    for subj, obj, rel in triplets:

        props: EdgeProperties = {
            # for provenance
            'sentence': sentence_text,
            **({'source': source} if source else {})  # only include if source is provided
            # 'original_sentence': getattr(source_doc, "page_content", ""),
            # **getattr(source_doc, "metadata", {})  # type: ignore[arg-type]
        }

        rels.append({
            "source": { "label": normalize_text(subj) },
            "target": { "label": normalize_text(obj) },
            "edge":   { "label": normalize_text(rel), "properties": props },
        }) # type: ignore

    return rels


def rows_to_graph_relations(
    rows: Iterable[Mapping[str, Any]],
    *,
    source_key: str = "source",
    target_key: str = "target",
    predicate_key: str = "predicate",
    props_key: str = "props",
    # if we want to enforce required props fields, will do it here
) -> List[GraphRelation]:
    rels: List[GraphRelation] = []

    for row in rows:
        source = row[source_key]
        target = row[target_key]
        predicate = row[predicate_key]
        props_raw = row.get(props_key, {}) or {}

        source_id = str(row.get("source_id", ""))
        target_id = str(row.get("target_id", ""))

        if not isinstance(props_raw, dict):
            raise TypeError(f"Expected '{props_key}' to be a dict, got {type(props_raw)}: {props_raw!r}")

        props: EdgeProperties = {**props_raw}  # type: ignore[misc]

        # Optional: keep predicate redundantly in properties for provenance/compat
        # (only if you want this invariant)
        props.setdefault("label", predicate)


        now = datetime.now().isoformat()
        rels.append(
            {
                "source": {
                    "label": str(source), 
                    "id": source_id,
                },
                "target": {
                    "label": str(target), 
                    "id": target_id,
                },
                "edge": {
                    "label": str(predicate), 
                    "properties": props
                }   
            } # type: ignore
        )

    return rels

