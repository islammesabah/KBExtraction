/**
 * Bootstrap confirmation dialogs
 * ------------------------------
 * Small helpers to show a modal and resolve a boolean decision.
 */

/**
 * Ask user to confirm overwriting cached triplets.
 *
 * @returns {Promise<boolean>} true if user confirms, else false.
 */
export function confirmOverwriteTriplets() {
    return new Promise((resolve) => {
        if (!window.bootstrap) {
            // Fallback if bootstrap isn't available for some reason.
            resolve(window.confirm("There are already extracted triplets. Re-extract and overwrite them?"));
            return;
        }

        const modalEl = document.getElementById("confirm-overwrite-triplets");
        const continueBtn = document.getElementById("confirm-overwrite-triplets-continue");

        if (!modalEl || !continueBtn) {
            resolve(true); // if modal missing, don't block workflow
            return;
        }

        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);

        let decided = false;

        const cleanup = () => {
            continueBtn.removeEventListener("click", onContinue);
            modalEl.removeEventListener("hidden.bs.modal", onHidden);
        };

        const onContinue = () => {
            decided = true;
            cleanup();
            modal.hide();
            resolve(true);
        };

        const onHidden = () => {
            // If modal closes without clicking continue => treat as cancel
            if (!decided) resolve(false);
            cleanup();
        };

        continueBtn.addEventListener("click", onContinue, { once: true });
        modalEl.addEventListener("hidden.bs.modal", onHidden, { once: true });

        modal.show();
    });
}