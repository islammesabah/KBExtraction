/**
 * Oversight State
 * --------------
 * Holds lightweight run context so later stages (triplets upsert) can attach provenance.
 *
 * We store in BOTH:
 * - in-memory (fast)
 * - localStorage (survives refresh)
 */

const KEY = "kbdebugger.oversight.run_context";

let ctx = null;

/**
 * @typedef {Object} RunContext
 * @property {string} source Provenance string, e.g. uploaded PDF filename or server corpus identifier.
 */

/** @param {RunContext} newCtx */
export function setRunContext(newCtx) {
    ctx = newCtx;
    try {
        localStorage.setItem(KEY, JSON.stringify(newCtx));
    } catch (_) {
        // ignore storage failures
    }
}

/** @returns {RunContext|null} */
export function getRunContext() {
    if (ctx) return ctx;

    try {
        const raw = localStorage.getItem(KEY);
        if (!raw) return null;
        ctx = JSON.parse(raw);
        return ctx;
    } catch (_) {
        return null;
    }
}

/** Clears context (optional, e.g., when new upload starts). */
export function clearRunContext() {
    ctx = null;
    try {
        localStorage.removeItem(KEY);
    } catch (_) { }
}

// --- Utils ---
export function getOversightSource() {
    return getRunContext()?.source_name ?? null;
}

export function getKeyword() {
    return getRunContext()?.keyword ?? null;
}

