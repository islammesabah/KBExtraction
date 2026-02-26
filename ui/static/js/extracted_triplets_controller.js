/**
 * Extracted Triplets Controller
 * -----------------------------
 * Responsible for rendering and managing the "Extracted Triplets" review UI:
 * - Shows/hides the correct Oversight sections
 * - Flattens pipeline extraction results into editable rows
 * - Inline editing for (subject, predicate, object)
 * - Allows deleting rows (soft delete)
 * - Provides submit-to-KG payload of cleaned triplets
 *
 * Expected server result shape (from job.result):
 * {
 *   extracted_triplets: [
 *     { sentence: string, triplets: [[subj, obj, pred], ...] }  // NOTE: Our current tuple order is [S, O, P]
 *   ]
 * }
 *
 * This controller normalizes each triplet row to:
 * { id, sentence, subject, predicate, object, deleted }
 */

import { upsertTripletsToKnowledgeGraphJob, getJobStatus } from "./pipeline_client.js";
import { showOversightOverlay, hideOversightOverlay } from "./oversight_overlay.js";
import { getRunContext } from "./oversight_state.js";

function getOversightSource() {
    // return getRunContext()?.source ?? null;
    return getRunContext()?.source_name ?? null;
}

/** Internal in-memory store of editable rows. */
const state = {
    rows: [],       // Array<TripletRow>
    filter: "",     // current filter string
    deletedCount: 0 // derived
};

/**
 * @typedef {Object} TripletRow
 * @property {string} id Unique stable row id.
 * @property {string} sentence Source sentence (from the extraction result).
 * @property {string} subject Editable subject.
 * @property {string} predicate Editable predicate.
 * @property {string} object Editable object.
 * @property {boolean} deleted Soft delete flag.
 */

/**
 * Generate a stable-ish id for a triplet row.
 * Uses sentence + SPO fields; good enough for UI row identity.
 */
function rowId({ sentence, subject, predicate, object }, idx) {
    return `${idx}::${sentence}::${subject}::${predicate}::${object}`;
}

/**
 * Given job.result.extracted_triplets, flatten to TripletRow[].
 * Our backend currently returns triplets in order: [subject, object, predicate].
 * We normalize to subject/predicate/object for editing UI.
 *
 * @param {any} extractedTripletsList job.result.extracted_triplets
 * @returns {TripletRow[]}
 */
function normalizeExtractionResult(extractedTripletsList) {
    const rows = [];
    let idx = 0;

    (extractedTripletsList || []).forEach(item => {
        const sentence = (item?.sentence ?? "").trim();
        const triplets = item?.triplets ?? [];

        triplets.forEach(t => {
            const s = String(t?.[0] ?? "").trim();
            const o = String(t?.[1] ?? "").trim();
            const p = String(t?.[2] ?? "").trim();

            // Skip empty junk rows defensively
            if (!s || !p || !o) return;

            const row = {
                id: rowId({ sentence, subject: s, predicate: p, object: o }, idx++),
                sentence,
                subject: s,
                predicate: p,
                object: o,
                deleted: false,
            };

            rows.push(row);
        });
    });

    return rows;
}

/**
 * Show/hide the candidate qualities section.
 * Here we interpret "candidate section" as the top container with inner tabs + submit.
 * In Our markup, that's `.oversight-top`.
 */
function setShowCandidateQualitiesSection(show) {
    const section = document.querySelector(".oversight-top");
    if (!section) return;
    section.classList.toggle("d-none", !show);
}

/** Show/hide the extracted triplets review section. */
function setShowExtractedTripletsSection(show) {
    const section = document.getElementById("oversight-bottom");
    if (!section) return;
    section.classList.toggle("d-none", !show);
}

/**
 * Public entrypoint:
 * Call this when triplet extraction job finishes (job.state === "done").
 *
 * @param {any} jobResult job.result (from GET /jobs/<id>)
 */
export function renderExtractedTripletsFromJobResult(jobResult) {
    const extractedTriplets = jobResult?.extracted_triplets ?? [];

    state.rows = normalizeExtractionResult(extractedTriplets);
    state.filter = "";

    // Switch UI sections
    setShowCandidateQualitiesSection(false);
    setShowExtractedTripletsSection(true);

    // Render
    wireTripletsToolbar(); // idempotent
    renderTripletsTable();
    updateTripletsCounters();
}

/**
 * Wire toolbar buttons + filter input once.
 * Safe to call multiple times (listeners are set with "once" guards).
 */
function wireTripletsToolbar() {
    const backBtn = document.getElementById("triplets-back");
    if (backBtn && !backBtn.dataset.wired) {
        backBtn.dataset.wired = "1";
        backBtn.addEventListener("click", () => {
            // go back to qualities selection UI
            setShowExtractedTripletsSection(false);
            setShowCandidateQualitiesSection(true);
        });
    }

    const filterInput = document.getElementById("triplets-filter");
    if (filterInput && !filterInput.dataset.wired) {
        filterInput.dataset.wired = "1";
        filterInput.addEventListener("input", () => {
            state.filter = (filterInput.value ?? "").trim().toLowerCase();
            renderTripletsTable();
            updateTripletsCounters();
        });
    }

    const clearBtn = document.getElementById("triplets-clear-filter");
    if (clearBtn && !clearBtn.dataset.wired) {
        clearBtn.dataset.wired = "1";
        clearBtn.addEventListener("click", () => {
            state.filter = "";
            const inp = document.getElementById("triplets-filter");
            if (inp) inp.value = "";
            renderTripletsTable();
            updateTripletsCounters();
        });
    }

    const submitBtn = document.getElementById("triplets-submit");
    if (submitBtn && !submitBtn.dataset.wired) {
        submitBtn.dataset.wired = "1";
        submitBtn.addEventListener("click", async () => {
            await submitTripletsToKG();
        });
    }
}

/**
 * Apply filter + hide deleted rows? (We keep deleted visible but greyed, so user can undo later.)
 * Filtering checks subject/predicate/object/sentence.
 */
function getVisibleRows() {
    const q = state.filter;
    if (!q) return state.rows;

    return state.rows.filter(r => {
        const hay = `${r.subject} ${r.predicate} ${r.object} ${r.sentence}`.toLowerCase();
        return hay.includes(q); // i.e., show the row if the filter query is a substring of any of the fields 
    });
}

/** Render the editable triplets table into #triplets-table-wrap. */
function renderTripletsTable() {
    const wrap = document.getElementById("triplets-table-wrap");
    const empty = document.getElementById("triplets-empty");
    if (!wrap) return;

    const rows = getVisibleRows();

    if (empty) empty.classList.toggle("d-none", rows.length !== 0);
    wrap.innerHTML = "";

    if (rows.length === 0) return;

    const table = document.createElement("table");
    table.className = "table table-hover align-middle";

    table.innerHTML = `
    <thead>
      <tr>
        <th style="width: 44px;"></th>
        <th>Subject</th>
        <th>Predicate</th>
        <th>Object</th>
        <th style="width: 84px;" class="text-end">Actions</th>
      </tr>
    </thead>
    <tbody></tbody>
  `;

    const tbody = table.querySelector("tbody");

    rows.forEach(r => {
        const tr = document.createElement("tr");
        // if (r.deleted) tr.classList.add("opacity-50"); // soft-delete: visually indicate deleted rows but keep them visible

        if (r.deleted) {
            btn.classList.remove("btn-outline-danger");
            btn.classList.add("btn-outline-secondary");
            btn.title = "Undo delete";
            btn.innerHTML = `<i class="bi bi-arrow-counterclockwise"></i>`;
        } else {
            btn.classList.remove("btn-outline-secondary");
            btn.classList.add("btn-outline-danger");
            btn.title = "Delete row";
            btn.innerHTML = `<i class="bi bi-trash"></i>`;
        }

        tr.innerHTML = `
      <td>
        <button type="button"
          class="btn btn-sm btn-link p-0 text-muted"
          data-bs-toggle="popover"
          data-bs-trigger="focus"
          data-bs-placement="right"
          data-bs-title="Source sentence"
          data-bs-content="${escapeHtml(r.sentence || "No sentence.")}">
          <i class="bi bi-chat-left-text"></i>
        </button>
      </td>

      <td>${editableCell("subject", r)}</td>
      <td>${editableCell("predicate", r)}</td>
      <td>${editableCell("object", r)}</td>

      <td class="text-end">
        <div class="btn-group btn-group-sm">
          <button type="button" class="btn btn-sm btn-outline-danger triplet-toggle-delete" title="Delete row">
            <i class="bi bi-trash"></i>
          </button>
        </div>
      </td>
    `;

        // Wire delete button
        const btn = tr.querySelector(".triplet-toggle-delete");
        btn.addEventListener("click", () => {
            r.deleted = !r.deleted;
            renderTripletsTable();
            updateTripletsCounters();
        });

        // Wire inline edits
        wireEditableInputs(tr, r);

        tbody.appendChild(tr);
    });

    wrap.appendChild(table);

    initBootstrapPopovers(wrap);
}

/**
 * Render a Bootstrap-styled editable input for a field.
 * We use input-sm to keep the table compact.
 */
function editableCell(field, row) {
    const value = escapeHtml(row[field] ?? "");
    const disabled = row.deleted ? "disabled" : "";
    return `
    <input
      type="text"
      class="form-control form-control-sm"
      data-field="${field}"
      value="${value}"
      ${disabled}
    />
  `;
}

/**
 * After row HTML is inserted, attach listeners to inputs to update state.
 * @param {HTMLElement} tr
 * @param {TripletRow} row
 */
function wireEditableInputs(tr, row) {
    tr.querySelectorAll("input[data-field]").forEach(inp => {
        inp.addEventListener("input", () => {
            const field = inp.dataset.field;
            const v = (inp.value ?? "").trim();
            row[field] = v;
            updateTripletsCounters();
        });
    });
}

/**
 * Update counters + enable/disable KG submit button.
 * Rules:
 * - Only count rows that are NOT deleted AND have non-empty S/P/O.
 */
function updateTripletsCounters() {
    const countEl = document.getElementById("triplets-count");
    const delEl = document.getElementById("triplets-deleted-count");
    const submitBtn = document.getElementById("triplets-submit");

    const deleted = state.rows.filter(r => r.deleted).length;

    const valid = state.rows.filter(r => {
        if (r.deleted) return false;
        return Boolean(r.subject?.trim() && r.predicate?.trim() && r.object?.trim());
    }).length;

    if (countEl) countEl.textContent = String(valid);
    if (delEl) delEl.textContent = String(deleted);

    if (submitBtn) submitBtn.disabled = (valid === 0);
}

/**
 * Build the payload to send to the server for KG upsert.
 *
 * The Python upsert expects: Sequence[ExtractionResult], where each item is:
 *   { sentence: str, triplets: [(subject, object, predicate), ...] }
 *
 * We therefore:
 * - drop deleted rows
 * - drop rows with missing S/P/O
 * - group remaining rows by sentence
 * - emit `extractions` in the exact expected shape
 *
 * @returns {{ extractions: Array<{sentence: string, triplets: Array<[string,string,string]>}>, source?: string }}
 */
function buildUpsertPayload() {
    const rows = state.rows
        .filter(r => !r.deleted)
        .map(r => ({
            sentence: (r.sentence ?? "").trim(),
            subject: (r.subject ?? "").trim(),
            predicate: (r.predicate ?? "").trim(),
            object: (r.object ?? "").trim(),
        }))
        .filter(r => r.sentence && r.subject && r.predicate && r.object);

    /** @type {Map<string, Array<[string,string,string]>>} */
    const bySentence = new Map();

    for (const r of rows) {
        if (!bySentence.has(r.sentence)) bySentence.set(r.sentence, []);
        // IMPORTANT: backend expects (Subject, Object, Predicate)
        bySentence.get(r.sentence).push([r.subject, r.object, r.predicate]);
    }

    // const extractions = Array.from(bySentence.entries()).map(([sentence, triplets]) => ({
    //     sentence,
    //     triplets,
    // }));

    // Before submitting, we might want to deduplicate identical triplets inside each sentence (LLM sometimes repeats):
    for (const [sentence, triplets] of bySentence.entries()) {
        const seen = new Set();
        const uniq = [];
        for (const t of triplets) {
            const key = t.join("||");
            if (seen.has(key)) continue;
            seen.add(key);
            uniq.push(t);
        }
        bySentence.set(sentence, uniq);
    }

    const source = getOversightSource();

    return source ? { extractions, source } : { extractions };
}

/**
 * Submit edited triplets to server for KG upsert (Stage 7).
 * Uses the same job polling pattern as Stage 6.
 */
async function submitTripletsToKG() {
    const payload = buildUpsertPayload();
    if (!payload.extractions.length) {
        alert("No valid triplets to submit.");
        return;
    }

    showOversightOverlay("Upserting triplets…", "Inserting reviewed triplets into the Knowledge Graph.");

    try {
        const start = await upsertTripletsToKnowledgeGraphJob(payload);
        const jobId = start.job_id;

        while (true) {
            const job = await getJobStatus(jobId);
            if (job.state === "done") {
                console.log("KG upsert done:", job.result);
                alert("✅ Triplets inserted into KG.");
                break;
            }
            if (job.state === "error") {
                throw new Error(job.error || "KG upsert failed.");
            }
            await sleep(1000);
        }
    } catch (e) {
        alert(e.message || String(e));
    } finally {
        hideOversightOverlay();
    }
}

function initBootstrapPopovers(root) {
    if (!window.bootstrap) return;
    root.querySelectorAll('[data-bs-toggle="popover"]').forEach(el => {
        new bootstrap.Popover(el);
    });
}

function escapeHtml(str) {
    return String(str ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function sleep(ms) {
    return new Promise(res => setTimeout(res, ms));
}