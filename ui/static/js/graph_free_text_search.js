/**
 * graph_search.js
 * --------------
 * Optional module: free-text search a node via server endpoint
 * and highlight it in the Cytoscape graph.
 *
 * Keep it optional so we can remove it later without touching main.js.
 */

/**
 * Wire the graph search input/button to a server endpoint and Cytoscape highlighting.
 *
 * @param {Object} params
 * @param {import("cytoscape").Core} params.cy - Cytoscape instance.
 * @param {string} params.searchBtnId - Search button ID.
 * @param {string} params.searchInputId - Search input ID.
 * @param {string} params.detailsContentId - Details panel container ID.
 * @param {string} params.endpoint - POST endpoint returning {details: string[]} or {error: string}.
 */
export function wireGraphSearch({
  cy,
  searchBtnId,
  searchInputId,
  detailsContentId,
  endpoint = "/api/search_node",
}) {
  if (!cy) return;

  const searchBtn = document.getElementById(searchBtnId);
  const searchInput = document.getElementById(searchInputId);
  const detailsContent = document.getElementById(detailsContentId);

  // If UI isn't present, silently do nothing.
  if (!searchBtn || !searchInput || !detailsContent) return;

  const resetUI = () => {
    cy.elements().removeClass("faded highlighted");
    detailsContent.innerHTML =
      '<p class="placeholder-text">Select a node or search to view details.</p>';
  };

  const renderDetails = (data) => {
    if (data.details && data.details.length > 0) {
      detailsContent.innerHTML = data.details
        .map((item) => `<div class="detail-item">${item}</div>`)
        .join("");
    } else {
      detailsContent.innerHTML = "<p>No details found for this node.</p>";
    }
  };

  const highlightNode = (query) => {
    cy.elements().removeClass("highlighted").addClass("faded");

    const targetNode = cy
      .nodes()
      .filter((n) => n.data("label") === query || n.data("id") === query);

    if (targetNode.length === 0) return;

    targetNode.removeClass("faded").addClass("highlighted");
    const neighborhood = targetNode.neighborhood();
    neighborhood.removeClass("faded").addClass("highlighted");

    cy.animate({
      fit: {
        eles: targetNode.union(neighborhood),
        padding: 50,
      },
    });
  };

  const performSearch = async () => {
    const query = (searchInput.value || "").trim();
    if (!query) {
      resetUI();
      return;
    }

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: query }),
      });

      const data = await response.json();

      if (data.error) {
        detailsContent.innerHTML = `<p style="color:red">Error: ${data.error}</p>`;
        return;
      }

      renderDetails(data);
      highlightNode(query);
    } catch (err) {
      console.error(err);
      detailsContent.innerHTML =
        `<p style="color:red">Error connecting to server.</p>`;
    }
  };

  searchBtn.addEventListener("click", performSearch);
  searchInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") performSearch();
  });
}
