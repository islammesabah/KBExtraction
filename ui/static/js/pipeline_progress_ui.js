/**
 * UI helpers for progress panel.
 */

export function showProgressPanel() {
  document.getElementById("pipeline-progress").classList.remove("hidden");
}

export function hideProgressPanel() {
  document.getElementById("pipeline-progress").classList.add("hidden");
}

export function updateProgressPanel({ stage, message, current, total }) {
  const stageEl = document.getElementById("pipeline-stage");
  const msgEl = document.getElementById("pipeline-message");
  const barEl = document.getElementById("pipeline-bar");
  const metaEl = document.getElementById("pipeline-meta");

  stageEl.textContent = stage || "Stage";
  msgEl.textContent = message || "";

  if (typeof current === "number" && typeof total === "number" && total > 0) {
    const pct = Math.max(0, Math.min(100, Math.round((current / total) * 100)));
    barEl.style.width = `${pct}%`;
    metaEl.textContent = `${current}/${total} (${pct}%)`;
  } else {
    // Indeterminate stage (e.g., Docling)
    barEl.style.width = "35%";
    metaEl.textContent = "Working…";
  }
}
