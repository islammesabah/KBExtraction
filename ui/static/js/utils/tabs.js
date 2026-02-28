/**
 * Tabs utilities
 * --------------
 * Helpers for switching Bootstrap tabs in a type-safe way (via JSDoc unions).
 */

/**
 * @typedef {"graph-view-tab" | "oversight-view-tab"} TopLevelTabId
 */

/**
 * Canonical IDs for the top-level view tabs.
 * Use these constants instead of raw strings in the rest of the codebase.
 *
 * @type {{ GRAPH: TopLevelTabId, OVERSIGHT: TopLevelTabId }}
 */
export const TopLevelTabs = Object.freeze({
    GRAPH: "graph-view-tab",
    OVERSIGHT: "oversight-view-tab",
});

/**
 * Switch to a top-level view tab (Graph / Oversight).
 *
 * Uses Bootstrap's Tab API when available, otherwise falls back to a native click.
 *
 * @param {Object} opts
 * @param {TopLevelTabId} opts.tab - Which top-level tab to activate.
 *
 * @example
 * switchToTopLevelTab({ tab: TopLevelTabs.GRAPH });
 * switchToTopLevelTab({ tab: TopLevelTabs.OVERSIGHT });
 */
export function switchToTopLevelTab({ tab }) {
    const btn = document.getElementById(tab);

    if (!btn) {
        console.warn(`[switchToTopLevelTab] Tab button not found: ${tab}`);
        return;
    }

    if (window.bootstrap?.Tab) {
        bootstrap.Tab.getOrCreateInstance(btn).show();
        return;
    }

    // Fallback safety (should rarely happen)
    btn.click();
}
