/**
 * Keyword dropdown:
 * - loads keywords from /api/search-keywords
 * - populates <select>
 * - on change: calls /api/subgraph and updates the graph
 */

import { getSearchKeywords, getSubgraph } from "./graph_client.js";

export async function initKeywordDropdown({
  selectId = "keyword-select",
  onGraphPayload,
  defaultKeyword = null
}) {
  const select = document.getElementById(selectId);
  if (!select) throw new Error(`Missing select element #${selectId}`);

  try {
    const data = await getSearchKeywords();
    const keywords = data.keywords || [];

    // Populate select
    select.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Select keyword...";
    select.appendChild(placeholder);

    for (const k of keywords) {
      const opt = document.createElement("option");
      opt.value = k;
      opt.textContent = k;
      select.appendChild(opt);
    }

    select.disabled = false;

    // Decide initial selection
    const initial =
      (defaultKeyword && keywords.includes(defaultKeyword) && defaultKeyword) ||
      (keywords.length > 0 ? keywords[0] : null);

    if (initial) {
      select.value = initial;
      await fetchAndRender(initial, onGraphPayload);
    }

    // On change
    select.addEventListener("change", async () => {
      const chosen = select.value.trim();
      if (!chosen) return; // user chose placeholder
      await fetchAndRender(chosen, onGraphPayload);
    });
  } catch (err) {
    console.error(err);
    select.innerHTML = `<option value="">❌ Failed to load keywords</option>`;
    select.disabled = true;
  }
}

async function fetchAndRender(keyword, onGraphPayload) {
  try {
    const payload = await getSubgraph(keyword);
    // payload is CytoscapeGraphPayload -> { elements: { nodes, edges } }
    onGraphPayload(payload);
  } catch (err) {
    console.error(err);
    alert(`Subgraph error: ${err.message}`);
  }
}
