/**
 * Graph controller:
 * - creates the Cytoscape instance
 * - updates graph elements when new payload arrives
 */

import { renderEmptyDetails, renderEdgeDetails, renderNodeDetails } from "./sidebar.js";
import { createStyledCytoscape } from "./cytoscape_theme.js";

import { getLastSubgraphPayload } from "./state/graph_state.js";
import { getKeyword } from "./state/oversight_state.js";
import { exportSubgraphSentencesAsJson, exportSubgraphSentencesAsTxt } from "./utils/export_utils.js";
import { showToast } from "./toast.js";


export function createCytoscapeGraph(containerId = "cy", detailsContainerId = "details-content") {
  const detailsEl = document.getElementById(detailsContainerId);
  if (detailsEl) renderEmptyDetails(detailsEl);

  const containerEl = document.getElementById(containerId);
  if (!containerEl) throw new Error(`Missing Cytoscape container #${containerId}`);

  const { cy, theme } = createStyledCytoscape(containerEl);

  const highlightEdgeAndRenderDetails = (edge) => {
    cy.elements().removeClass("highlighted-node highlighted-edge");

    edge.addClass("highlighted-edge");
    edge.source().addClass("highlighted-node");
    edge.target().addClass("highlighted-node");

    if (detailsEl) renderEdgeDetails(detailsEl, edge.data());
  }

  function selectEdgeById(edgeId) {
    const edge = cy.getElementById(edgeId);
    if (!edge || edge.empty()) return;

    highlightEdgeAndRenderDetails(edge);
  }

  const highlightNodeAndRenderDetails = (node) => {
    cy.elements().removeClass("highlighted-node highlighted-edge");
    node.addClass("highlighted-node");

    const incidentEdges = node.connectedEdges().toArray();

    if (!detailsEl) return;


    try {
      renderNodeDetails(detailsEl, node.data(), incidentEdges, (edgeId) => {
        // onRelationPick callback passed to renderNodeDetails will be called 
        // when user clicks on an incident edge in the details panel
        selectEdgeById(edgeId);
      });
    } catch (err) {
      console.error("[panel] renderNodeDetails crashed:", err);
    }
  }

  cy.on("tap", "edge", (evt) => highlightEdgeAndRenderDetails(evt.target));
  cy.on("tap", "node", (evt) => highlightNodeAndRenderDetails(evt.target));

  // Optional: click background -> clear selection
  cy.on("tap", (evt) => {
    if (evt.target !== cy) return;
    cy.elements().removeClass("highlighted-node highlighted-edge");
    if (detailsEl) renderEmptyDetails(detailsEl);
  });

  // Bonus: also allow double-click background to reset
  cy.on("dbltap", (evt) => {
    if (evt.target !== cy) return;
    resetZoomToInitialView();
  });

  function resetZoomToInitialView() {
    cy.fit(undefined, 150);
  }

  const resetZoomBtn = document.getElementById("reset-zoom-btn");
  if (resetZoomBtn) {
    resetZoomBtn.addEventListener("click", () => {
      resetZoomToInitialView();
    });
  }

  function wireGraphExportButtons() {
    const btnJson = document.getElementById("export-subgraph-json");
    const btnTxt = document.getElementById("export-subgraph-txt");

    if (btnJson && !btnJson.dataset.wired) {
      btnJson.dataset.wired = "1";
      btnJson.addEventListener("click", () => {
        const payload = getLastSubgraphPayload();
        const keyword = getKeyword();

        const res = exportSubgraphSentencesAsJson({ subgraphPayload: payload, keyword });
        if (!res.ok) {
          showToast({ type: "warning", title: "Nothing to export 😅", message: res.reason });
          return;
        }
        showToast({ type: "success", title: "Exported ✅", message: `Downloaded ${res.count} sentences as JSON 📦` });
      });
    }

    if (btnTxt && !btnTxt.dataset.wired) {
      btnTxt.dataset.wired = "1";
      btnTxt.addEventListener("click", () => {
        const payload = getLastSubgraphPayload();

        // Since getKeyword() is only set after pipeline runs, then Graph-tab export might have keyword=null 
        // when user only browses graph. If that’s the case, use the dropdown selected value instead:
        const keyword = getKeyword() ?? (document.getElementById("keyword-select")?.value?.trim() || null);

        const res = exportSubgraphSentencesAsTxt({ subgraphPayload: payload, keyword });
        if (!res.ok) {
          showToast({ type: "warning", title: "Nothing to export 😅", message: res.reason });
          return;
        }
        showToast({ type: "success", title: "Exported ✅", message: `Downloaded ${res.count} sentences as TXT 📝` });
      });
    }
  }

  wireGraphExportButtons();

  function setGraph(elements) {
    /**
     * Expected payload format from server:
     * {
          "elements": {
            "edges": [...],
            "nodes": [...]
          }
        }
     */
    const emptyOverlay = document.getElementById("graph-empty-state");

    // Clear current graph then add new elements
    cy.elements().remove();

    const hasNodes = elements?.nodes?.length > 0;
    const hasEdges = elements?.edges?.length > 0;

    const setShowEmptyState = (show) => {
      if (!emptyOverlay) return;

      show ? emptyOverlay.classList.remove("d-none") : emptyOverlay.classList.add("d-none");
    };

    if (!hasNodes && !hasEdges) {
      // Show empty state
      setShowEmptyState(true);
      return;
    }

    // Hide empty state
    setShowEmptyState(false);

    cy.add(elements);

    cy.layout({
      name: 'cose',
      animate: true
    }).run();

    // Fit the graph to the viewport with padding
    // undefined means fit all elements, 150 is the padding.
    // Sometimes fitting immediately while layout is animating can feel jumpy. You can delay fit slightly:
    setTimeout(() => {
      cy.fit(undefined, 150);
    }, 250);
  }

  // Return theme too in case we want it later
  return { cy, setGraph, theme };
}
