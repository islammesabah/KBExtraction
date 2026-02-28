/**
 * Oversight overlay (Bootstrap modal)
 * -----------------------------------
 * Replaces the old section-scoped custom overlay with a Bootstrap modal.
 *
 * Why:
 * - Better readability (proper dimmed backdrop)
 * - Consistent UX with the global overlay modal
 * - Avoids "DOM not ready" issues by lazy-initializing elements
 *
 * Requirements:
 * - bootstrap.bundle.min.js must be loaded (you already do).
 * - index.html must contain #oversight-loading-modal and title/subtitle ids.
 */

let _modal = null;

/**
 * Lazily create/get the Bootstrap modal instance.
 * @returns {import("bootstrap").Modal | null}
 */
function getModalInstance() {
  const el = document.getElementById("oversight-loading-modal");
  if (!el || !window.bootstrap) return null;

  // Create once
  if (!_modal) {
    _modal = new bootstrap.Modal(el, {
      backdrop: "static",
      keyboard: false,
      focus: true,
    });

    // Optional: tint only this modal's backdrop (adds class to the generated backdrop)
    el.addEventListener("shown.bs.modal", () => {
      const backdrops = document.querySelectorAll(".modal-backdrop");
      const last = backdrops[backdrops.length - 1];
      if (last) last.classList.add("oversight-backdrop");
    });

    el.addEventListener("hidden.bs.modal", () => {
      const backdrops = document.querySelectorAll(".modal-backdrop.oversight-backdrop");
      // Remove only one (the most recent) to avoid messing with other modals
      const last = backdrops[backdrops.length - 1];
      if (last) last.classList.remove("oversight-backdrop");
    });
  }

  return _modal;
}

/**
 * Show the Oversight loading modal with text.
 * @param {string} [title]
 * @param {string} [subtitle]
 */
export function showOversightOverlay(title, subtitle) {
  const titleEl = document.getElementById("oversight-modal-title");
  const subEl = document.getElementById("oversight-modal-subtitle");

  if (titleEl) titleEl.textContent = title || "Working…";
  if (subEl) subEl.textContent = subtitle || "Please wait.";

  const modal = getModalInstance();
  modal?.show();
}

/**
 * Hide the Oversight loading modal.
 */
export function hideOversightOverlay() {
  const modal = getModalInstance();
  modal?.hide();
}