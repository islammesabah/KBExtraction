// timer.js
// Tracks and renders an elapsed timer for the pipeline progress panel.

function formatElapsed(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds));
  const hh = Math.floor(s / 3600);
  const mm = Math.floor((s % 3600) / 60);
  const ss = s % 60;

  if (hh > 0) {
    return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
  }
  return `${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
}

let pipelineStartedAtMs = null;
let elapsedTimerHandle = null;

function tick() {
  const el = document.getElementById("pipeline-elapsed");
  if (!el) return;

  if (!pipelineStartedAtMs) {
    el.textContent = "⏱️ 00:00";
    return;
  }

  const elapsedSec = (Date.now() - pipelineStartedAtMs) / 1000;
  el.textContent = `⏱️ ${formatElapsed(elapsedSec)}`;
}

function startElapsedTimer() {
  if (elapsedTimerHandle) return;
  // update immediately so it doesn't wait 250ms for first paint
  tick();
  elapsedTimerHandle = setInterval(tick, 250);
}

function stopElapsedTimer() {
  if (!elapsedTimerHandle) return;
  clearInterval(elapsedTimerHandle);
  elapsedTimerHandle = null;
}

/**
 * Call this ONCE when a new pipeline run is started (after clicking upload).
 * It resets internal state and UI.
 */
export function resetElapsedTimer() {
  pipelineStartedAtMs = null;
  const el = document.getElementById("pipeline-elapsed");
  if (el) el.textContent = "⏱️ 00:00";
  stopElapsedTimer();
}

/**
 * Call this on every poll response, passing the status object `st`.
 * Expected fields:
 * - job.started_at (ISO string, optional but recommended)
 * - job.state in {"queued","running","done","error"}
 */
export function updateElapsedTimer(job) {
  // latch start time once
  if (job?.started_at && !pipelineStartedAtMs) {
    pipelineStartedAtMs = Date.parse(job.started_at);
  }

  // If backend doesn't send started_at yet, we can fallback to "now"
  // once we see the first "running" status.
  if (!pipelineStartedAtMs && job?.state === "running") {
    pipelineStartedAtMs = Date.now();
  }

  if (job?.state === "running" || job?.state === "queued") {
    startElapsedTimer();
  } else {
    // done / error: stop ticking but keep final value visible
    stopElapsedTimer();
    tick();
  }
}
