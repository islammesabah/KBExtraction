/**
 * Oversight controller
 * --------------------
 * Renders novelty results into the Oversight tab (3 subtabs) with:
 * - checkbox selection
 * - client-side pagination
 * - submit selected -> triplet extraction
 */

import { startTripletExtractionJob, getJobStatus } from "./pipeline_client.js"; // we’ll add startTripletExtractionJob
import { showOversightOverlay, hideOversightOverlay } from "./oversight_overlay.js";
import { switchToTab } from "./utils/tabs.js";

const PAGE_SIZE = 10;

// Keep selection across tabs/pages
const selected = new Map(); // key=stableId, value=QualityNoveltyResult

// function stableId(r, idx) {
//   // best-effort stable id: quality + idx fallback
//   return `${idx}::${r.decision}::${r.quality}`;
// }

function stableId(r) {
  const neighbor = r.matched_neighbor_sentence || "";
  return `${r.decision}::${r.quality}::${neighbor}`;
}

function groupByDecision(results) {
  const sortDesc = (a, b) => (b.max_score ?? 0) - (a.max_score ?? 0);

  const filterBy = (decision) =>
    results
      .filter(r => r.decision === decision)
      .sort(sortDesc);

  return {
    EXISTING: filterBy("EXISTING"),
    PARTIALLY_NEW: filterBy("PARTIALLY_NEW"),
    NEW: filterBy("NEW"),
  };
}

function paginate(items, page, pageSize) {
  const total = items.length;
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const p = Math.min(Math.max(1, page), pages);
  const start = (p - 1) * pageSize;
  return { page: p, pages, slice: items.slice(start, start + pageSize) };
}

function renderTable({ container, items, decisionKey, page }) {
  let isBulkToggle = false; // flag to prevent infinite loop when programmatically toggling checkboxes

  container.innerHTML = "";

  const { page: cur, pages, slice } = paginate(items, page, PAGE_SIZE);

  const tableWrap = document.createElement("div");
  tableWrap.className = "table-responsive";

  const table = document.createElement("table");
  table.className = "table table-hover align-middle mb-2";

  table.innerHTML = `
    <thead>
      <tr>
        <th style="width: 52px;">
          <input 
            class="form-check-input oversight-checkbox" 
            type="checkbox" 
            id="select-all-${decisionKey}-${cur}"
            title="Select all on this page" 
          />
        </th>
        <th>Quality</th>
        <th style="width: 130px;">
          Similarity
        <i 
          class="bi bi-info-circle ms-1 text-muted"
          data-bs-toggle="tooltip"
          data-bs-title="Cosine similarity between this quality sentence and the closest existing relation sentence in the retrieved KG subgraph. Higher = closer match."></i>
        </th>
      </tr>
    </thead>
    <tbody></tbody>
  `;

  const tbody = table.querySelector("tbody");

  slice.forEach((r, idxOnPage) => {
    const globalIdx = (cur - 1) * PAGE_SIZE + idxOnPage;
    // const id = stableId(r, globalIdx);
    const id = stableId(r);
    const checked = selected.has(id);

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>
        <input class="form-check-input oversight-checkbox" type="checkbox" ${checked ? "checked" : ""} />
      </td>
      <td class="quality-cell">
        <div class="fw-semibold fs-6 d-flex align-items-start gap-2">
          <button type="button"
            class="btn btn-sm btn-link p-0 text-muted"
            data-bs-toggle="popover"
            data-bs-trigger="focus"
            data-bs-placement="left"
            data-bs-title="Rationale"
            data-bs-content="${escapeHtml(r.rationale || "No rationale.")}">
            <i class="bi bi-info-circle"></i>
          </button>
          
          <span class="flex-grow-1">${escapeHtml(r.quality)}</span>
        </div>
      </td>
      <td>
        <span class="badge text-bg-secondary">${(r.max_score ?? 0).toFixed(2)}</span>
      </td>
    `;

    const cb = tr.querySelector("input[type=checkbox]");
    cb.addEventListener("change", () => {
      if (cb.checked) selected.set(id, r);
      else selected.delete(id);
      updateSelectedCount();

      // change the tr background color when selected for better UX
      tr.classList.toggle("table-active", cb.checked);
    });

    // Make the whole row clickable (not just tiny checkbox)
    tr.style.cursor = "pointer";

    tr.addEventListener("click", (e) => {
      // Don’t double-toggle if user clicked directly on checkbox or on buttons/icons
      if (e.target.closest("input[type=checkbox], button, a, i")) return;
      cb.checked = !cb.checked;
      cb.dispatchEvent(new Event("change", { bubbles: true }));

      // change the tr background color when selected for better UX
      tr.classList.toggle("table-active", cb.checked);
    });

    tbody.appendChild(tr);
  });


  // After we have appended all rows, we can add "select all" listener
  const selectAllCheckbox = table.querySelector(`#select-all-${decisionKey}-${cur}`);

  /**
   * Gets all checkboxes for the current page slice rows
   */
  const getRowCheckboxes = () => tbody.querySelectorAll('input[type="checkbox"]');

  // helper: compute select-all checkbox state for this page slice
  function syncSelectAllCheckboxState() {
    const rowCheckboxes = getRowCheckboxes();
    const checkedCount = Array.from(rowCheckboxes).filter(cb => cb.checked).length;

    if (checkedCount === 0) {
      selectAllCheckbox.checked = false;
      selectAllCheckbox.indeterminate = false;
    } else if (checkedCount === rowCheckboxes.length) {
      selectAllCheckbox.checked = true;
      selectAllCheckbox.indeterminate = false;
    } else {
      selectAllCheckbox.checked = false;
      selectAllCheckbox.indeterminate = true; // ✅ partial selection
    }
  }

  // initialize select-all state on render
  if (selectAllCheckbox) syncSelectAllCheckboxState();

  // when user clicks select-all => toggle all rows in this page
  if (selectAllCheckbox) {
    selectAllCheckbox.addEventListener("change", () => {
      const rowCheckboxes = getRowCheckboxes();

      isBulkToggle = true; // ✅ prevent header resync during bulk loop

      rowCheckboxes.forEach(cb => {
        if (cb.checked !== selectAllCheckbox.checked) {
          cb.checked = selectAllCheckbox.checked;
          // call dispatchEvent so each row's checkbox listener will run, updating the `selected` map accordingly.
          // i.e., programmatically toggling the checkbox doesn't trigger the "change" event by default, so we need to dispatch it manually.
          cb.dispatchEvent(new Event("change", { bubbles: true })); 
        }
      });

      isBulkToggle = false;

      // ✅ after bulk is done, sync header ONCE
      selectAllCheckbox.indeterminate = false;
    }); 
  }

  // whenever a row checkbox changes => keep select-all in sync
  getRowCheckboxes().forEach(cb => {
    cb.addEventListener("change", () => {
      if (isBulkToggle) return; // ✅ don't fight bulk operation
      syncSelectAllCheckboxState();
    });
  });

  tableWrap.appendChild(table);
  container.appendChild(tableWrap);

  // Pagination controls
  const pager = document.createElement("div");
  pager.className = "d-flex justify-content-between align-items-center";

  const left = document.createElement("div");
  left.className = "text-muted small";
  left.textContent = `${items.length} total • page ${cur}/${pages}`;

  const right = document.createElement("div");
  right.className = "btn-group btn-group-sm";

  const prev = document.createElement("button");
  prev.className = "btn btn-outline-secondary";
  prev.textContent = "Prev";
  prev.disabled = cur <= 1;
  prev.addEventListener("click", () => {
    renderDecision(decisionKey, cur - 1);
  });

  const next = document.createElement("button");
  next.className = "btn btn-outline-secondary";
  next.textContent = "Next";
  next.disabled = cur >= pages;
  next.addEventListener("click", () => {
    renderDecision(decisionKey, cur + 1);
  });

  right.appendChild(prev);
  right.appendChild(next);

  pager.appendChild(left);
  pager.appendChild(right);

  container.appendChild(pager);

  initBootstrapHints(container);

  function initBootstrapHints(root) {
    if (!window.bootstrap) return;

    root.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
      new bootstrap.Tooltip(el);
    });

    root.querySelectorAll('[data-bs-toggle="popover"]').forEach(el => {
      new bootstrap.Popover(el);
    });
  }
}

let grouped = null;

function renderDecision(decisionKey, page = 1) {
  const pane = document.querySelector(`#oversight-${decisionKey.toLowerCase()} .qualities-container`);
  if (!pane) return;
  renderTable({ container: pane, items: grouped[decisionKey], decisionKey, page });
}

function updateSelectedCount() {
  const el = document.getElementById("oversight-selected-count");
  if (el) el.textContent = String(selected.size);

  const btn = document.getElementById("oversight-submit");
  if (btn) btn.disabled = selected.size === 0;
}

/**
 * Public entrypoint: call this when pipeline finishes.
 */
export function renderHumanOversightFromPipelineResult(pipelineResult) {
  // One Small Improvement (Optional)
  // If a user re-runs the pipeline, you may want to:
  // - Clear previous selections
  // - Hide oversight-bottom
  // - Reset selected count
  
  // selected.clear();
  // setShowExtractedTripletsReviewSection(false);

  // So every run starts clean.

  const novelty = pipelineResult?.NoveltyLLM;
  const results = novelty?.results || [];

  grouped = groupByDecision(results);

  // Render each tab page 1
  renderDecision("EXISTING", 1);
  renderDecision("PARTIALLY_NEW", 1);
  renderDecision("NEW", 1);

  updateSelectedCount();

  switchToTab("oversight-view-tab");
}

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

// ------------------------------------------------------------------
// Submit selected -> triplet extraction (Stage 6 job)
// ------------------------------------------------------------------
// const setShowExtractedTripletsReviewSection = (show) => {
//   const section = document.getElementById("oversight-bottom");
//   if (!section) return;
//   section.classList.toggle("d-none", !show);
// };

export function wireHumanOversightSubmit({ keywordSelectId, fileInputId }) {
  const btn = document.getElementById("oversight-submit");
  if (!btn) return;

  btn.addEventListener("click", async () => {
    if (selected.size === 0) {
      alert("Select at least one quality first.");
      return;
    }

    // ❌
    // const payload = Array.from(selected.values()); // list of novelty results
    
    // Slim payload: just the quality strings
    const selected_qualities = Array.from(selected.values())
      .map(r => (r?.quality ?? "").trim())
      .filter(Boolean);

    if (selected_qualities.length === 0) {
      alert("Selected rows had no quality text.");
      return;
    }

    showOversightOverlay("Extracting triplets…", "This may take a minute.");

    try {
      const start = await startTripletExtractionJob({ selected_qualities });
      const jobId = start.job_id;

      // Poll until done (reuse same job API)
      while (true) {
        const job = await getJobStatus(jobId);
        if (job.state === "done") {
          // show extracted triplets UI + render editable table
          renderExtractedTripletsFromJobResult(job.result);
          break;
        }
        if (job.state === "error") {
          throw new Error(job.error || "Triplet extraction failed.");
        }
        await sleep(1000);
      }
    } catch (e) {
      alert(e.message || String(e));
    } finally {
      hideOversightOverlay();
    }
  });
}

function sleep(ms) {
  return new Promise(res => setTimeout(res, ms));
}
