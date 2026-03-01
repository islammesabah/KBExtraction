/**
 * Global Loading Modal
 * --------------------
 * Bootstrap-native "loading overlay" using a Modal.
 * - Dims the entire page properly
 * - Prevents interaction while active
 */

let _modal = null;

function getModal() {
    if (!window.bootstrap) throw new Error("Bootstrap JS is not loaded.");
    const el = document.getElementById("global-loading-modal");
    if (!el) throw new Error("Missing #global-loading-modal in DOM.");
    _modal = _modal || bootstrap.Modal.getOrCreateInstance(el);
    return { el, modal: _modal };
}

export function showGlobalLoading(title = "Loading…", subtitle = "Please wait.") {
    const { el, modal } = getModal();

    const t = el.querySelector("#overlay-title");
    const s = el.querySelector("#overlay-subtitle");
    if (t) t.textContent = title;
    if (s) s.textContent = subtitle;

    modal.show();
}

export function hideGlobalLoading() {
    const { modal } = getModal();
    modal.hide();
}
