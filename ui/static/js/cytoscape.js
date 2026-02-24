/**
 * Graph controller:
 * - creates the Cytoscape instance
 * - updates graph elements when new payload arrives
 */

import { renderEmptyDetails, renderEdgeDetails, renderNodeDetails } from "./concept_insights_panel.js";

export function createCytoscapeGraph(containerId = "cy", detailsContainerId = "details-content") {
  const detailsEl = document.getElementById(detailsContainerId);
  if (detailsEl) renderEmptyDetails(detailsEl);

  // Extract Bootstrap theme colors from CSS variables for consistent styling
  const rootStyles = getComputedStyle(document.documentElement);

  // Bootstrap 5 default colors with fallbacks
  const bsPrimary = rootStyles.getPropertyValue('--bs-primary').trim() || '#0d6efd';
  const bsSecondary = rootStyles.getPropertyValue('--bs-secondary').trim() || '#6c757d';
  const bsDanger = rootStyles.getPropertyValue('--bs-danger').trim() || '#dc3545';
  const bsLight = rootStyles.getPropertyValue('--bs-light').trim() || '#f8f9fa';
  const bsSuccess = rootStyles.getPropertyValue('--bs-success').trim() || '#198754';

  const cy = cytoscape({
    container: document.getElementById(containerId),
    style: [
      {
        selector: "node",
        style: {
          "background-color": bsPrimary,
          "label": "data(label)",
          "text-valign": "center",
          "text-halign": "center",
          "color": "#fff",
          "text-outline-width": 2,
          "text-outline-color": bsPrimary,
          "font-size": "12px",
          "width": "50px",
          "height": "50px"
        }
      },
      {
        selector: "edge",
        style: {
            'width': 2,
            'line-color': bsSecondary,
            'target-arrow-color': bsSecondary,
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': '10px',
            'text-rotation': 'autorotate',
            'text-background-opacity': 1,
            'text-background-color': bsLight,
            'text-background-padding': 2,
            'text-wrap': 'wrap',
            'text-max-width': 80
        }
      },
      // {
      //   selector: ".highlighted",
      //   style: {
      //     "background-color": bsSuccess,
      //     "line-color": bsSuccess,
      //     "target-arrow-color": bsSuccess,
      //     "transition-property": "background-color, line-color, target-arrow-color",
      //     "transition-duration": "0.2s"
      //   }
      // },
      {
        selector: ".highlighted",
        style: {
          // keep original colors, but add glow
          "shadow-blur": 18,
          "shadow-color": "#ffe066",     // highlighter yellow
          "shadow-opacity": 0.9,
          "shadow-offset-x": 0,
          "shadow-offset-y": 0,

          // edges: make them a bit bolder + glowing
          "width": 4,
          "line-color": "#ffc107",       // bootstrap warning-ish
          "target-arrow-color": "#ffc107",

          "transition-property": "shadow-blur, shadow-opacity, line-color, target-arrow-color, width",
          "transition-duration": "0.2s"
        }
      },
      {
        selector: ".faded",
        style: {
          "opacity": 0.1,
          "text-opacity": 0
        }
      }
    ],
    layout: {
        name: "cose",
        animate: true,
        // fit: true,
        // padding: 150, // adds space between the graph and the viewport border when fitting/zooming.

        idealEdgeLength: 180,
        nodeRepulsion: 10000,
        edgeElasticity: 80,
        gravity: 0.8,
        numIter: 1000
     }
  });

  const highlightEdgeAndRenderDetails = (edge) => {
    cy.elements().removeClass("highlighted");
    edge.addClass("highlighted");

    // Optionally: when edge is selected, highlight edge + its endpoints for clarity:
    edge.source().addClass("highlighted");
    edge.target().addClass("highlighted");

    if (detailsEl) renderEdgeDetails(detailsEl, edge.data());
  }

  function selectEdgeById(edgeId) {
    const edge = cy.getElementById(edgeId);
    if (!edge || edge.empty()) return;

    highlightEdgeAndRenderDetails(edge);
  }

  const highlightNodeAndRenderDetails = (node) => {
    cy.elements().removeClass("highlighted");
    node.addClass("highlighted");

    const incidentEdges = node.connectedEdges().toArray();

    if (detailsEl) {
      renderNodeDetails(detailsEl, node.data(), incidentEdges, (edgeId) => {
        // onEdgePick callback passed to renderNodeDetails will be called 
        // when user clicks "↗️ View" on an incident edge in the details panel
        selectEdgeById(edgeId);
      });
    }
  }

  // Click edge -> show edge properties
  cy.on("tap", "edge", (evt) => {
    const edge = evt.target;
    highlightEdgeAndRenderDetails(edge);
  });


  // Click node -> show node + list incident edges
  cy.on("tap", "node", (evt) => {
    const node = evt.target;
    highlightNodeAndRenderDetails(node);
  });

  // Optional: click background -> clear selection
  cy.on("tap", (evt) => {
    if (evt.target !== cy) return;
    cy.elements().removeClass("highlighted");
    if (detailsEl) renderEmptyDetails(detailsEl);
  });

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
    // undefined means fit all elements, 150 is the padding
    cy.fit(undefined, 150);
  }

  return { cy, setGraph };
}
