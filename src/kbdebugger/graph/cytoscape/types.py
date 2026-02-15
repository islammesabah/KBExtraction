from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, TypedDict
from typing_extensions import Required, NotRequired


# -----------------------------
# Cytoscape: Node
# -----------------------------
class CytoscapeNodeData(TypedDict):
    """
    Minimal node data required by Cytoscape.js.
    """
    id: str
    label: str

    # Optional: you can attach extra info for side-panels/tooltips later.
    properties: NotRequired[Dict[str, Any]]


class CytoscapeNode(TypedDict):
    data: CytoscapeNodeData


# -----------------------------
# Cytoscape: Edge
# -----------------------------
class CytoscapeEdgeData(TypedDict):
    """
    Minimal edge data required by Cytoscape.js.
    """
    id: str
    source: str
    target: str
    label: str

    # Optional: relationship properties (provenance, sentence, etc.)
    properties: NotRequired[Dict[str, Any]]


class CytoscapeEdge(TypedDict):
    data: CytoscapeEdgeData


# -----------------------------
# Cytoscape: Payload
# -----------------------------
class CytoscapeElements(TypedDict):
    nodes: List[CytoscapeNode]
    edges: List[CytoscapeEdge]


class CytoscapeGraphPayload(TypedDict):
    """
    What the UI should receive and pass directly to:
        cy.add(payload.elements)
    """
    elements: CytoscapeElements
    


@dataclass(frozen=True, slots=True)
class CytoscapeMappingConfig:
    """
    Mapping config for converting GraphRelation -> Cytoscape elements.

    Notes
    -----
    In your current GraphRelation contract, GraphEnd only has "label".
    So by default, node IDs will equal labels.

    If later you add stable IDs (Neo4j element_id, UUID, etc.), you can extend
    this mapping without touching UI code.
    """
    # If True, include edge properties (provenance, sentence, etc.) in payload
    include_edge_properties: bool = True

    # If True, include node properties in payload (currently not available in GraphRelation ends)
    include_node_properties: bool = False

    # Edge IDs: if False, we generate sequential e0,e1,...; if True, we try to derive from properties
    prefer_edge_id_from_properties: bool = True

    # Property key to use if prefer_edge_id_from_properties is True
    edge_id_property_key: str = "edge_id"
