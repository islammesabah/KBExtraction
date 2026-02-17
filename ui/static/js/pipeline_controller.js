/**
 * Orchestrates upload -> start job -> poll -> update UI.
 */

import { startPipelineJob, getJobStatus } from "./pipeline_client.js";
import { showProgressPanel, updateProgressPanel } from "./pipeline_progress_ui.js";

export function wirePipelineUpload({ fileInputId, keywordSelectId, onDone }) {
  const fileInput = document.getElementById(fileInputId);
  const keywordSel = document.getElementById(keywordSelectId);

  if (!fileInput) throw new Error(`Missing file input: #${fileInputId}`);
  if (!keywordSel) throw new Error(`Missing keyword select: #${keywordSelectId}`);

  fileInput.addEventListener("change", async () => {
    if (!fileInput.files || fileInput.files.length === 0) return;

    const keyword = keywordSel.value.trim();
    if (!keyword) {
      alert("🔍️ Please choose a keyword first.");
      return;
    }

    const file = fileInput.files[0];
    showProgressPanel();
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
        const st = await getJobStatus(jobId);
        updateProgressPanel({
          stage: st.stage,
          message: st.message,
          current: st.progress?.current ?? null,
          total: st.progress?.total ?? null,
        });

        
        if (st.state === "done") {
          onDone?.(st.result);
          return;
        }
        if (st.state === "error") {
          alert(`Pipeline failed: ${st.error || "unknown error"}`);
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
