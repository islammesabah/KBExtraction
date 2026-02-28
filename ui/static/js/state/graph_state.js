/**
 * Subgraph State 🧠
 * ---------------
 * Caches the latest `/api/graph/subgraph?keyword=...` response so other UI actions
 * (like exports) can reuse it without re-fetching or scraping Cytoscape.
 *
 * Why this exists
 * ---------------
 * - Export should be fast and deterministic ✅
 * - Export should work even if user didn't click any edge ✅
 * - Export should not depend on Cytoscape's internal graph model ✅
 */

/** @type {any|null} */
let _lastSubgraphPayload = null;

/**
 * Save the most recent subgraph payload returned from the server.
 *
 * @param {any} payload The raw JSON from `/api/graph/subgraph?keyword=...`.
 */
export function setLastSubgraphPayload(payload) {
    _lastSubgraphPayload = payload ?? null;
}

/**
 * Get the most recent cached subgraph payload.
 *
 * @returns {any|null}
 */
export function getLastSubgraphPayload() {
    return _lastSubgraphPayload;
}

/**
 * Clear cached payload (optional).
 * Useful if you want to "reset session" after pipeline completion.
 */
export function clearLastSubgraphPayload() {
    _lastSubgraphPayload = null;
}
