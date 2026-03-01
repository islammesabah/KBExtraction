/**
 * Confirm Modal 🧩
 * ---------------
 * A single reusable Bootstrap confirmation dialog.
 *
 * Usage:
 * const ok = await confirmModal({
 *   title: "⚠️ Reset session?",
 *   body: "This will erase the current pipeline session.",
 *   confirmText: "Yes, reset",
 *   confirmBtnClass: "btn-danger",
 * });
 * if (ok) { ... }
 */

/**
 * @typedef {Object} ConfirmModalOptions
 * @property {string} title
 * @property {string} body
 * @property {string} [confirmText="Continue"]
 * @property {string} [cancelText="Cancel"]
 * @property {string} [confirmBtnClass="btn-primary"] Bootstrap btn class, e.g. "btn-danger"
 */

/**
 * Show the reusable confirmation dialog and resolve with user's choice.
 *
 * @param {ConfirmModalOptions} opts
 * @returns {Promise<boolean>} true if confirmed, false otherwise.
 */
export function confirmModal(opts) {
    const modalEl = document.getElementById("confirm-modal");
    const titleEl = document.getElementById("confirm-modal-title");
    const bodyEl = document.getElementById("confirm-modal-body");
    const cancelEl = document.getElementById("confirm-modal-cancel");
    const confirmEl = document.getElementById("confirm-modal-confirm");

    if (!modalEl || !titleEl || !bodyEl || !cancelEl || !confirmEl) {
        // Fallback: browser confirm (never blocks functionality)
        // eslint-disable-next-line no-alert
        return Promise.resolve(window.confirm(`${opts.title}\n\n${opts.body}`));
    }

    titleEl.textContent = opts.title || "Confirm";
    bodyEl.textContent = opts.body || "Are you sure?";

    cancelEl.textContent = opts.cancelText || "Cancel";
    confirmEl.textContent = opts.confirmText || "Continue";

    // Reset + apply button class
    confirmEl.className = "btn";
    confirmEl.classList.add(opts.confirmBtnClass || "btn-primary");

    const bsModal = window.bootstrap?.Modal?.getOrCreateInstance(modalEl);

    return new Promise((resolve) => {
        let resolved = false;

        const cleanup = () => {
            confirmEl.removeEventListener("click", onConfirm);
            modalEl.removeEventListener("hidden.bs.modal", onHidden);
        };

        const onConfirm = () => {
            resolved = true;
            cleanup();
            bsModal?.hide();
            resolve(true);
        };

        const onHidden = () => {
            // If user closed the modal without pressing confirm → cancel
            if (!resolved) resolve(false);
            cleanup();
        };

        confirmEl.addEventListener("click", onConfirm);
        modalEl.addEventListener("hidden.bs.modal", onHidden);

        bsModal?.show();
    });
}
