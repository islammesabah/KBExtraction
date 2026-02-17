/**
 * UI helpers for progress panel.
 * 
 * Assumes #pipeline-bar is a Bootstrap .progress-bar element.
 */

const INDETERMINATE_CLASSES = ["progress-bar-striped", "progress-bar-animated"];

const pipelineProgress = document.getElementById("pipeline-progress")

export function showProgressPanel() {
  // document.getElementById("pipeline-progress").classList.remove("hidden");
  pipelineProgress.classList.remove("d-none");
}

export function hideProgressPanel() {
  // document.getElementById("pipeline-progress").classList.add("hidden");
  pipelineProgress.classList.add("d-none");
}

export function updateProgressPanel({ stage, message, current, total }) {
  const stageEl = document.getElementById("pipeline-stage");
  const msgEl = document.getElementById("pipeline-message");
  const barEl = document.getElementById("pipeline-bar");
  const metaEl = document.getElementById("pipeline-meta");

  stageEl.textContent = stage || "Stage";
  msgEl.textContent = message || "";

  const hasNumbers = typeof current === "number" && typeof total === "number" && total > 0;

  if (hasNumbers) {
    // Determinate progress
    barEl.classList.remove(...INDETERMINATE_CLASSES);

    const pct = Math.max(0, Math.min(100, Math.round((current / total) * 100)));
    barEl.style.width = `${pct}%`;
    barEl.setAttribute("aria-valuenow", String(pct));
    barEl.setAttribute("aria-valuemin", "0");
    barEl.setAttribute("aria-valuemax", "100");

    metaEl.textContent = `${current}/${total} (${pct}%)`;
  } else {
    // Indeterminate progress (unknown total / unknown current)
    barEl.classList.add(...INDETERMINATE_CLASSES);

    // Bootstrap doesn't have true indeterminate, so we animate stripes at full width
    barEl.style.width = "100%";
    barEl.setAttribute("aria-valuenow", "100");
    barEl.setAttribute("aria-valuemin", "0");
    barEl.setAttribute("aria-valuemax", "100");

    metaEl.textContent = "Working…";
  }
}