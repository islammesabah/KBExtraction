/**
 * Graph Refresh Bridge
 * --------------------
 * This module avoids tight coupling between:
 * - main.js (where Cytoscape instance lives)
 * - other controllers (oversight / extracted_triplets)
 *
 * main.js registers a renderer callback once.
 * Any module can then call refreshGraphForKeyword(keyword) to refetch + re-render.
 */

import { getSubgraph } from "./graph_client.js";

let _renderSubgraph = null;

/**
 * Register a callback that knows how to render the subgraph payload.
 * Call this once from main.js after Cytoscape graph is created.
 *
 * @param {(payload: any) => void} fn
 */
export function registerSubgraphRenderer(fn) {
    _renderSubgraph = fn;
}

/**
 * Refetch and re-render the graph for a keyword.
 *
 * @param {string} keyword
 */
export async function refreshGraphForKeyword(keyword) {
    if (!_renderSubgraph) {
        throw new Error("Graph renderer not registered. Did you call registerSubgraphRenderer() in main.js?");
    }
    const payload = await getSubgraph(keyword);
    _renderSubgraph(payload);
}
