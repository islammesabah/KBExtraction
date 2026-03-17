/**
 * Export Utils 📦
 * --------------
 * Small utilities to export data from the UI as downloadable files (JSON/TXT).
 *
 * Design goals
 * ------------
 * - No server required ✅
 * - Works offline / local ✅
 * - One-liners from controllers ✅
 */

/**
 * @typedef {Object} SubgraphSentenceRecord
 * @property {string} sentence
 * @property {string} [source]
 * @property {number|null} [page_number]
 * @property {string} [relation]
 * @property {string|null} [created_at]
 * @property {string|null} [last_updated_at]
 */

/**
 * Download a JSON object as a `.json` file.
 *
 * @param {Object} opts
 * @param {string} opts.filename
 * @param {any} opts.data
 */
export function downloadJson({ filename, data }) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    _downloadBlob(blob, filename);
}

/**
 * Download a string as a UTF-8 `.txt` file.
 *
 * @param {Object} opts
 * @param {string} opts.filename
 * @param {string} opts.text
 */
export function downloadText({ filename, text }) {
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    _downloadBlob(blob, filename);
}

/**
 * Export subgraph edge sentences as JSON.
 *
 * Output shape:
 * {
 *   keyword: string|null,
 *   exported_at: string,   // ISO timestamp
 *   sentences: Array<SubgraphSentenceRecord>
 * }
 *
 * @param {Object} opts
 * @param {any} opts.subgraphPayload Raw payload from `/api/graph/subgraph`.
 * @param {string|null} opts.keyword Current keyword (for convenience).
 * @param {string} [opts.filename] Optional override filename.
 * @returns {{ ok: true, count: number } | { ok: false, reason: string }}
 */
export function exportSubgraphSentencesAsJson({ subgraphPayload, keyword, filename }) {
    const sentences = _extractSubgraphSentenceRecords(subgraphPayload);

    if (sentences.length === 0) {
        return { ok: false, reason: "No edge sentences found in the current subgraph." };
    }

    const safeKey = _safeSlug(keyword || "keyword");
    const out = {
        keyword: keyword ?? null,
        exported_at: new Date().toISOString(),
        sentences,
    };

    downloadJson({
        filename: filename || `kbdebugger_subgraph_sentences_${safeKey}.json`,
        data: out,
    });

    return { ok: true, count: sentences.length };
}

/**
 * Export subgraph edge sentences as TXT (unique sentences).
 *
 * TXT format:
 * 1. sentence...
 *
 * 2. sentence...
 *
 * @param {Object} opts
 * @param {any} opts.subgraphPayload Raw payload from `/api/graph/subgraph`.
 * @param {string|null} opts.keyword Current keyword (for convenience).
 * @param {string} [opts.filename] Optional override filename.
 * @returns {{ ok: true, count: number } | { ok: false, reason: string }}
 */
export function exportSubgraphSentencesAsTxt({ subgraphPayload, keyword, filename }) {
    const records = _extractSubgraphSentenceRecords(subgraphPayload);
    const uniq = Array.from(new Set(records.map(r => r.sentence).filter(Boolean)));

    if (uniq.length === 0) {
        return { ok: false, reason: "No edge sentences found in the current subgraph." };
    }

    const safeKey = _safeSlug(keyword || "keyword");
    const text = uniq.map((s, i) => `${i + 1}. ${s}`).join("\n\n");

    downloadText({
        filename: filename || `kbdebugger_subgraph_sentences_${safeKey}.txt`,
        text,
    });

    return { ok: true, count: uniq.length };
}

/* ------------------------- internal helpers ------------------------- */

/**
 * Extract sentence records from the server subgraph payload.
 *
 * We prefer `properties.sentence`, but fall back to `original_sentence`.
 *
 * @param {any} payload
 * @returns {SubgraphSentenceRecord[]}
 */
function _extractSubgraphSentenceRecords(payload) {
    const edges = payload?.elements?.edges ?? [];
    /** @type {SubgraphSentenceRecord[]} */
    const out = [];

    for (const e of edges) {
        const props = e?.data?.properties ?? null;
        if (!props) continue;

        const sentence = String(props.sentence || props.original_sentence || "").trim();
        if (!sentence) continue;

        out.push({
            sentence,
            source: props.source || "",
            page_number: (props.page_number ?? null),
            relation: props.label || props.relation || "",
            created_at: props.created_at ?? null,
            last_updated_at: props.last_updated_at ?? null,
        });
    }

    return out;
}

/**
 * Download a Blob via an invisible anchor.
 *
 * @param {Blob} blob
 * @param {string} filename
 */
function _downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();

    URL.revokeObjectURL(url);
}

/**
 * Make a filename-safe slug.
 *
 * @param {string} s
 * @returns {string}
 */
function _safeSlug(s) {
    return String(s)
        .trim()
        .replaceAll(/\s+/g, "_")
        .replaceAll(/[^a-zA-Z0-9_\-]/g, "");
}


/**
 * Export candidate oversight sentences as TXT.
 *
 * Each line corresponds to one table row sentence.
 *
 * TXT format:
 * 1. sentence...
 *
 * 2. sentence...
 *
 * @param {Object} opts
 * @param {string[]} opts.sentences
 * @param {string|null} [opts.keyword]
 * @param {string} [opts.filename]
 * @returns {{ ok: true, count: number } | { ok: false, reason: string }}
 */
export function exportSentencesAsTxt({ sentences, keyword, filename }) {
    const clean = Array.from(
        new Set(
            (sentences || [])
                .map(s => String(s || "").trim())
                .filter(Boolean)
        )
    );

    if (clean.length === 0) {
        return { ok: false, reason: "No sentences found to export." };
    }

    const safeKey = _safeSlug(keyword || "keyword");
    const text = clean.map((s, i) => `${i + 1}. ${s}`).join("\n\n");

    downloadText({
        filename: filename || `kbdebugger_candidate_sentences_${safeKey}.txt`,
        text,
    });

    return { ok: true, count: clean.length };
}

/**
 * Export candidate oversight sentences grouped by decision.
 *
 * TXT format:
 * === NEW ===
 * 1. sentence
 *
 * === PARTIALLY NEW ===
 * 1. sentence
 *
 * === EXISTING ===
 * 1. sentence
 *
 * @param {Object} opts
 * @param {Object} opts.grouped
 * @param {string|null} [opts.keyword]
 * @param {string} [opts.filename]
 * @returns {{ ok: true, count: number } | { ok: false, reason: string }}
 */
export function exportGroupedSentencesAsTxt({ grouped, keyword, filename }) {
    if (!grouped) {
        return { ok: false, reason: "No sentences available." };
    }

    const order = ["NEW", "PARTIALLY_NEW", "EXISTING"];

    const sections = [];

    for (const key of order) {
        const items = grouped[key] || [];
        const sentences = Array.from(
            new Set(
                items
                    .map(r => String(r?.quality || "").trim())
                    .filter(Boolean)
            )
        );

        if (sentences.length === 0) continue;

        const header = key.replaceAll("_", " ");
        const body = sentences
            .map((s, i) => `${i + 1}. ${s}`)
            .join("\n\n");

        sections.push(`=== ${header} ===\n\n${body}`);
    }

    if (sections.length === 0) {
        return { ok: false, reason: "No sentences found to export." };
    }

    const text = sections.join("\n\n\n");

    const safeKey = _safeSlug(keyword || "keyword");

    downloadText({
        filename: filename || `kbdebugger_candidate_sentences_${safeKey}.txt`,
        text,
    });

    return { ok: true, count: sections.length };
}


/**
 * Export candidate oversight rows into ONE Excel sheet.
 *
 * Columns:
 * - Group
 * - Sentence
 * - Similarity
 *
 * @param {Object} opts
 * @param {Object} opts.grouped
 * @param {string|null} [opts.keyword]
 * @param {string} [opts.filename]
 * @returns {{ ok: true, count: number } | { ok: false, reason: string }}
 */
export function exportGroupedSentencesAsXlsx({ grouped, keyword, filename }) {
    if (!grouped) {
        return { ok: false, reason: "No candidate sentences available." };
    }

    const XLSX_LIB = globalThis.XLSX;
    if (!XLSX_LIB) {
        return { ok: false, reason: "XLSX export is not available because SheetJS is not loaded." };
    }

    const orderedGroups = [
        { key: "NEW", label: "New" },
        { key: "PARTIALLY_NEW", label: "Partially New" },
        { key: "EXISTING", label: "Existing" },
    ];

    /** @type {{Group: string, Sentence: string, Similarity: number}[]} */
    const rows = [];

    for (const group of orderedGroups) {
        const items = dedupeRowsBySentenceKeepBestScore(grouped[group.key] || []);

        for (const r of items) {
            const sentence = String(r?.quality || "").trim();
            if (!sentence) continue;

            rows.push({
                Group: group.label,
                Sentence: sentence,
                Similarity: Number((r?.max_score ?? 0).toFixed(2)),
            });
        }
    }

    if (rows.length === 0) {
        return { ok: false, reason: "No candidate sentences found to export." };
    }

    const wb = XLSX_LIB.utils.book_new();
    const ws = XLSX_LIB.utils.json_to_sheet(rows);

    XLSX_LIB.utils.book_append_sheet(wb, ws, "Candidate Sentences");

    const safeKey = _safeSlug(keyword || "keyword");
    const outName = filename || `kbdebugger_candidate_sentences_${safeKey}.xlsx`;

    XLSX_LIB.writeFile(wb, outName);

    return { ok: true, count: rows.length };
}

/**
 * Deduplicate rows by sentence text, keeping the highest-similarity row.
 *
 * @param {any[]} items
 * @returns {any[]}
 */
function dedupeRowsBySentenceKeepBestScore(items) {
    const bestByKey = new Map();

    for (const r of items || []) {
        const sentence = String(r?.quality || "").trim();
        const key = sentence.toLowerCase();
        if (!sentence) continue;

        const existing = bestByKey.get(key);
        if (!existing || (r?.max_score ?? 0) > (existing?.max_score ?? 0)) {
            bestByKey.set(key, r);
        }
    }

    return Array.from(bestByKey.values());
}