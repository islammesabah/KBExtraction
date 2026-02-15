"""
Graph-related API routes.

Responsibilities
---------------
- Serve Cytoscape-ready graph payloads.
- Serve curated search keywords for dropdown selection.

Design principles
-----------------
- No Neo4j driver usage here.
- No retrieval internals here.
- Only stage API calls + presentation adapters.
"""

from __future__ import annotations

import os
from flask import Blueprint, jsonify, request, render_template

from kbdebugger.graph.api import retrieve_keyword_subgraph_cytoscape
from ..services.search_keywords_service import load_search_keywords
from ..services.pipeline_config_service import get_pipeline_config

graph_bp = Blueprint("graph", __name__) 
# name does not affect the URL path.
# Only the url_prefix in app.register_blueprint(...) controls that.

@graph_bp.get("/")
def index():
    """
    Render the main UI page.
    """
    return render_template("index.html")


@graph_bp.get("/search-keywords")
def api_search_keywords():
    """
    Return the list of allowed Trustworthy-AI keywords for the UI dropdown.

    Returns
    -------
    JSON
        {"keywords": ["Human agency and oversight", ...]}
    """
    try:
        keywords = load_search_keywords()
        return jsonify({"keywords": keywords})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@graph_bp.get("/subgraph")
def api_subgraph():
    """
    Retrieve a keyword-driven KG subgraph.

    Query Parameters
    ----------------
    keyword : str
        Must match one of the curated search keywords.

    Returns
    -------
    JSON
        CytoscapeGraphPayload:
        {
            "elements": {
                "nodes": [...],
                "edges": [...]
            }
        }
    """
    keyword = (request.args.get("keyword") or "").strip()
    # ✅ this reads a query parameter from URL.
    # Example:
    #   /api/subgraph?keyword=Transparency
    if not keyword:
        return jsonify({"error": "Missing query param: keyword"}), 400

    allowed_keywords = set(load_search_keywords())
    if keyword not in allowed_keywords:
        return jsonify({"error": f"Keyword not allowed: {keyword!r}\n Allowed keywords: {sorted(allowed_keywords)}"}), 400

    try:
        cfg = get_pipeline_config()

        payload = retrieve_keyword_subgraph_cytoscape(
            keyword=keyword,
            limit_per_pattern=cfg.kg_limit_per_pattern,
        )

        return jsonify(payload)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
