/**
 * Orchestrates upload -> start job -> poll -> update UI.
 */

import { startPipelineJob, getJobStatus } from "./pipeline_client.js";
import { showProgressPanel, updateProgressPanel } from "./pipeline_progress_ui.js";
import { resetElapsedTimer, updateElapsedTimer } from "./timer.js";
import { setRunContext } from "./oversight_state.js";

export function wirePipelineUpload({ fileInputId, keywordSelectId, onDone }) {
  const fileInput = document.getElementById(fileInputId);
  const keywordSel = document.getElementById(keywordSelectId);

  if (!fileInput) throw new Error(`Missing file input: #${fileInputId}`);
  if (!keywordSel) throw new Error(`Missing keyword select: #${keywordSelectId}`);

  if (fileInput.disabled) {
    fileInput.title = "🔐 Select a keyword first";
  }

  fileInput.addEventListener("change", async () => {
    if (!fileInput.files || fileInput.files.length === 0) return;

    const keyword = keywordSel.value.trim();
    if (!keyword) {
      alert("🔍️ Please choose a keyword first.");
      return;
    }

    const file = fileInput.files[0];
    showProgressPanel();
    resetElapsedTimer();
    updateProgressPanel({ stage: "queued", message: "Queued…", current: null, total: null });

    let jobId;
    try {
      const startResp = await startPipelineJob({ keyword, file });
      jobId = startResp.job_id;
    } catch (err) {
      alert(`Failed to start pipeline: ${err.message}`);
      return;
    }

    // Poll
    const poll = async () => {
      try {
        const job = await getJobStatus(jobId);

        updateProgressPanel({
          stage: job.stage,
          message: job.message,
          current: job.progress?.current ?? null,
          total: job.progress?.total ?? null,
        });

        updateElapsedTimer(job);

        if (job.state === "done") {
          // ✅ Save provenance for downstream stages (triplets upsert, etc.)
          const meta = job.result?._meta;
          if (meta?.source) {
            setRunContext({
              source: meta.source,
              source_name: meta.source_name || null,
              keyword: meta.keyword || null,
            });
          }

          onDone?.(job.result);
          return;
        }
        if (job.state === "error") {
          alert(`Pipeline failed: ${job.error || "unknown error"}`);
          return;
        }

        // setTimeout(poll, 700); // 0.7s polling is smooth enough
        setTimeout(poll, 1000);
      } catch (err) {
        alert(`Lost connection while polling: ${err.message}`);
      }
    };

    poll();
  });
}
