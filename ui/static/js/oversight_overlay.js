/**
 * Oversight overlay
 * -----------------
 * Lightweight overlay shown during long Stage 6 calls.
 */

const overlay = document.getElementById("oversight-overlay");
const titleEl = document.getElementById("oversight-overlay-title");
const subEl = document.getElementById("oversight-overlay-subtitle");

export function showOversightOverlay(title, subtitle) {
  if (titleEl) titleEl.textContent = title || "Working…";
  if (subEl) subEl.textContent = subtitle || "";
  if (overlay) overlay.classList.remove("d-none");
}

export function hideOversightOverlay() {
  if (overlay) overlay.classList.add("d-none");
}
