/**
 * Main entrypoint:
 * - initialize graph controller (Cytoscape)
 * - initialize keyword dropdown and connect it to graph updates
 *
 * Keep this file tiny.
 */

import { createCytoscapeGraph } from "./cytoscape.js";
import { initKeywordDropdown } from "./keyword_dropdown.js";
import { wirePipelineUpload } from "./pipeline_controller.js";

// Optional modules (TODO: Most likely will be deleted)
import { wireGraphSearch } from "./graph_free_text_search.js";
import { wireOversightLegacy } from "./oversight_legacy.js"; // keep disabled unless needed


document.addEventListener("DOMContentLoaded", async () => {
  // ---------------------------------------------------------------------------
  // 1) Graph initialize (Cytoscape)
  // ---------------------------------------------------------------------------
  const graph = createCytoscapeGraph("cy", "details-content");

  // ---------------------------------------------------------------------------
  // 2) Keyword dropdown => fetch subgraph => update Cytoscape
  // ---------------------------------------------------------------------------
  await initKeywordDropdown({
    selectId: "keyword-select",
    defaultKeyword: null, // optionally set e.g. "Transparency"
    onSubgraphFetch: (payload) => {
      // payload.elements should match Cytoscape format: { nodes: [...], edges: [...] }
      graph.setGraph(payload.elements);
    },
  });

  // ---------------------------------------------------------------------------
  // 3) Pipeline upload
  // ---------------------------------------------------------------------------
  wirePipelineUpload({
    fileInputId: "documents",
    keywordSelectId: "keyword-select", // whatever your dropdown id is
    onDone: (result) => {
      console.log("Pipeline result:", result);
      // Later: feed Stage 4 novelty results into our 3 tabs directly.
    },
  });


  // ---------------------------------------------------------------------------
  // 4) Optional: graph free-text search (if you keep that UI)
  // ---------------------------------------------------------------------------
  wireGraphSearch({
    cy: graph.cy, // relies on createCytoscapeGraph exposing cy
    searchBtnId: "search-btn",
    searchInputId: "node-search",
    detailsContentId: "details-content",
    endpoint: "/api/search_node",
  });


  // // ---------------------------------------------------------------------------
  // // 5) Optional: legacy/supervisor oversight logic (keep disabled for now)
  // // ---------------------------------------------------------------------------
  // wireOversightLegacy({
  //   fileInputId: "documents",
  //   verificationSectionId: "verification-section",
  //   commonVerifiedListId: "common-verified-list",
  //   endpoint: "/api/upload_verify",
  // });
});
