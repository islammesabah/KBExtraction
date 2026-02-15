from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple

from kbdebugger.types import GraphRelation
from kbdebugger.types.base import GraphEnd
from kbdebugger.utils.json import to_jsonable

from .types import (
    CytoscapeEdge,
    CytoscapeGraphPayload,
    CytoscapeNode,
    CytoscapeMappingConfig,
)


"""
A utility module to convert GraphRelation objects into Cytoscape.js format for visualization in the UI.
"""
def _fallback_node_id(label: str, *, prefix: str) -> str:
    """
    Deterministic fallback if elementId is missing.
    We hash to avoid huge IDs and to keep it stable across runs.
    """
    h = hashlib.sha1(label.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}{h}"
    

def _node_key(label: str, element_id: Optional[str], *, cfg: CytoscapeMappingConfig) -> Tuple[str, str]:
    """
    Returns:
      (cy_id, display_label)

    Cytoscape ID must be unique + stable.
    Prefer elementId if provided; else deterministic label hash.
    """
    if element_id and element_id.strip():
        return (element_id.strip(), label)
    return (_fallback_node_id(label, prefix=cfg.fallback_id_prefix), label)


def graph_relations_to_cytoscape(
    relations: List[GraphRelation],
    *,
    cfg: CytoscapeMappingConfig | None = None,
) -> CytoscapeGraphPayload:
    """
    Convert GraphRelation list into a strict CytoscapeGraphPayload.

    Uses GraphEnd.id as the node ID whenever available.
    """
    cfg = cfg or CytoscapeMappingConfig()

    nodes: List[CytoscapeNode] = []
    edges: List[CytoscapeEdge] = []
    seen_node_ids: Set[str] = set()

    def ensure_node(end: GraphEnd) -> str:
        """
        Ensure node exists, return its Cytoscape node id.
        """
        label: str = end["label"]
        id: Optional[str] = end.get("id")

        node_id, display_label = _node_key(label, id, cfg=cfg)

        if node_id not in seen_node_ids:
            seen_node_ids.add(node_id)

            node: CytoscapeNode = {
                "data": {
                    "id": node_id,
                    "label": display_label,
                }
            }

            if cfg.include_node_properties:
                # Keep it small; we include a few useful fields.
                node["data"]["properties"] = {
                    "id": id,
                    "created_at": end.get("created_at"),
                    "last_updated_at": end.get("last_updated_at"),
                }

            nodes.append(node)

        return node_id

    for idx, rel in enumerate(relations):
        src_end = rel["source"]
        tgt_end = rel["target"]

        src_id = ensure_node(src_end)
        tgt_id = ensure_node(tgt_end)

        edge_label = rel["edge"]["label"]
        edge_props = rel["edge"].get("properties") or {}

        edge: CytoscapeEdge = {
            "data": {
                "id": f"e{idx}",  # OK; edges are per-response unique
                "source": src_id,
                "target": tgt_id,
                "label": edge_label,
            }
        }

        if cfg.include_edge_properties and edge_props:
            edge["data"]["properties"] = dict(edge_props)

        edges.append(edge)

    payload: CytoscapeGraphPayload = {"elements": {"nodes": nodes, "edges": edges}}
    
    return to_jsonable(payload)
