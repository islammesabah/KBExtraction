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
  onSubgraphFetch,
  useGlobalOverlay = false,
  // defaultKeyword = null
}) {
  const select = document.getElementById(selectId);
  if (!select) throw new Error(`Missing select element #${selectId}`);

  const fileInput = document.getElementById("documents");
  const keywordSpinner = document.getElementById("keyword-spinner");

  const overlay = document.getElementById("global-loading-overlay");
  const overlayTitle = document.getElementById("overlay-title");
  const overlaySubtitle = document.getElementById("overlay-subtitle");

  // Helper: enable/disable upload UI
  function setUploadEnabled(enabled) {
    if (fileInput) fileInput.disabled = !enabled;
  }

  function setLoading(isLoading, { title = "Loading…", subtitle = "Please wait." } = {}) {
    // 1. Disable dropdown while pending to avoid multi-clicks / duplicate requests
    select.disabled = isLoading;

    // 2. Show/hide inline spinner near dropdown
    if (keywordSpinner) keywordSpinner.classList.toggle("d-none", !isLoading);

    // 3. Also disable upload while graph is loading (optional but recommended)
    if (fileInput) fileInput.disabled = isLoading || fileInput.disabled;

    // 4. Global overlay (optional)
    if (useGlobalOverlay && overlay) {
      overlay.classList.toggle("d-none", !isLoading);
      if (overlayTitle) overlayTitle.textContent = title;
      if (overlaySubtitle) overlaySubtitle.textContent = subtitle;
    }
  }

  // Default: upload disabled until keyword chosen
  setUploadEnabled(false);
  
  try {
    setLoading(true, { title: "Loading keywords…", subtitle: "Populating the keyword list." });
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
    //   await fetchAndRenderSubgraph(initial, onSubgraphFetch);
    // }

    // On keyword change: enable upload + fetch/render graph
    select.addEventListener("change", async () => {
      const chosen = select.value.trim();
      
      // If somehow empty, keep upload disabled
      if (!chosen) {
        setUploadEnabled(false);
        return;
      }

      // Enable upload once keyword is chosen (but we may temporarily disable during loading)
      setUploadEnabled(true);

      // Now the user has selected a keyword from the dropdown, we can show loading state while fetching the subgraph
      setLoading(true, {
        title: "Loading graph…",
        subtitle: "If the database is waking up, this may take a moment.",
      });

      try {
        // Fetch and render subgraph for the chosen keyword
        await fetchAndRenderSubgraph(chosen, onSubgraphFetch);
      } finally {
        setLoading(false);
        // Re-enable upload after load finishes
        setUploadEnabled(true);
      }
    });
  } catch (err) {
    console.error(err);
    select.innerHTML = `<option value="">❌ Failed to load keywords</option>`;
    select.disabled = true;
    setUploadEnabled(false);
  } finally {
    // Stop loading overlay/spinner after keyword list attempt
    setLoading(false);
  }
}

let currentSubgraphAbort = null;

async function fetchAndRenderSubgraph(keyword, onSubgraphFetch) {
  try {
    if (currentSubgraphAbort) currentSubgraphAbort.abort();
    currentSubgraphAbort = new AbortController();

    const subgraphPayload = await getSubgraph(keyword, { signal: currentSubgraphAbort.signal });
    // payload is CytoscapeGraphPayload -> { elements: { nodes, edges } }
    onSubgraphFetch(subgraphPayload);
  } catch (err) {
    if (err.name === "AbortError") return; // ignore
    console.error(err);
    alert(`Subgraph error: ${err.message}`);
  }
  finally {
    currentSubgraphAbort = null;
  }
}
