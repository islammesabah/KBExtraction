/**
 * Keyword dropdown:
 * - loads keywords from /api/search-keywords
 * - populates <select>
 * - DOES NOT auto-select any keyword
 * - enables upload ONLY after a keyword is selected
 * - on change: calls /api/subgraph and updates the graph
 */

import { getSearchKeywords, getSubgraph } from "./graph_client.js";

export async function initKeywordDropdown({
  selectId = "keyword-select",
  onGraphPayload,
  // defaultKeyword = null
}) {
  const select = document.getElementById(selectId);
  if (!select) throw new Error(`Missing select element #${selectId}`);

  const fileInput = document.getElementById("documents");
  const uploadLabel = document.getElementById("upload-label");

  // Helper: enable/disable upload UI
  function setUploadEnabled(enabled) {
    if (fileInput) fileInput.disabled = !enabled;
    if (uploadLabel) {
      uploadLabel.classList.toggle("disabled", !enabled);
      uploadLabel.setAttribute("aria-disabled", String(!enabled));
      uploadLabel.title = enabled ? "📄 Upload Documents" : "🔐 Select a keyword first";
    }
  }

  // Default: upload disabled until keyword chosen
  setUploadEnabled(false);
  
  try {
    const data = await getSearchKeywords();
    const keywords = data.keywords || [];

    // Populate select
    select.innerHTML = "";

    // Placeholder: selected + disabled => user must pick something else
    const placeholder = document.createElement("option");
    placeholder.value = "";
    // placeholder.textContent = "— Select a keyword —";
    placeholder.textContent = "🔐 Select a keyword";
    placeholder.disabled = true;
    placeholder.selected = true;
    select.appendChild(placeholder);

    for (const k of keywords) {
      const opt = document.createElement("option");
      opt.value = k;
      opt.textContent = k;
      select.appendChild(opt);
    }

    select.disabled = false;

    // 🟥 IMPORTANT: no auto-selection, no auto-fetch here.

    // // Decide initial selection
    // const initial =
    //   (defaultKeyword && keywords.includes(defaultKeyword) && defaultKeyword) ||
    //   (keywords.length > 0 ? keywords[0] : null);

    // if (initial) {
    //   select.value = initial;
    //   await fetchAndRender(initial, onGraphPayload);
    // }

    // On change: enable upload + fetch/render graph
    select.addEventListener("change", async () => {
      const chosen = select.value.trim();
      
      // If somehow empty, keep upload disabled
      if (!chosen) {
        setUploadEnabled(false);
        return;
      }

      // Enable upload once keyword is chosen
      setUploadEnabled(true);

      // Fetch and render subgraph for the chosen keyword
      await fetchAndRender(chosen, onGraphPayload);
    });``
  } catch (err) {
    console.error(err);
    select.innerHTML = `<option value="">❌ Failed to load keywords</option>`;
    select.disabled = true;
    setUploadEnabled(false);
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
