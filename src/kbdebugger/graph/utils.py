from kbdebugger.types import EdgeProperties, ExtractionResult, GraphRelation
from kbdebugger.compat.langchain import Document
from typing import List, Iterable, Mapping, Any


def _normalize_label(text: str) -> str:
    """
    Normalize a free-text label into a safe identifier:
    - lowercase
    - strip punctuation at edges
    # - collapse spaces -> underscores
    """
    clean = " ".join(text.split()).strip().lower()
    # clean = clean.replace(" ", "_")
    return clean


def map_extracted_triplets_to_graph_relations(
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
            "source": { "label": _normalize_label(subj) },
            "target": { "label": _normalize_label(obj) },
            "edge":   { "label": _normalize_label(rel), "properties": props },
        })

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

        if not isinstance(props_raw, dict):
            raise TypeError(f"Expected '{props_key}' to be a dict, got {type(props_raw)}: {props_raw!r}")

        props: EdgeProperties = {**props_raw}  # type: ignore[misc]

        # Optional: keep predicate redundantly in properties for provenance/compat
        # (only if you want this invariant)
        props.setdefault("label", predicate)

        rels.append(
            {
                "source": {"label": str(source)},
                "target": {"label": str(target)},
                "edge": {"label": str(predicate), "properties": props},
            }
        )

    return rels

