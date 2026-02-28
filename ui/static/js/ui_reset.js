/**
 * UI Reset
 * --------
 * Resets the UI after a successful end-to-end run (KG upsert done).
 *
 * What it resets:
 * - Upload input (so user can re-upload the same file and trigger change)
 * - Oversight run context (localStorage + memory)
 * - Oversight stepper UI (back to Step 1 / hide Step 2)
 * - Oversight controller selections (selected map + counters)
 * - Extracted triplets cache + UI
 */

import { clearRunContext } from "./state/oversight_state.js";
import { resetHumanOversightUI } from "./oversight_controller.js";
import { resetExtractedTripletsUI } from "./extracted_triplets_controller.js";
import { setOversightStep, OversightSteps } from "./oversight_stepper.js";

/**
 * Reset the whole "pipeline session" after KG upsert.
 *
 * @param {Object} opts
 * @param {string} [opts.fileInputId="documents"] - File input element id.
 */
export function resetPipelineSession({ fileInputId = "documents" } = {}) {
    // 1) clear provenance/context
    clearRunContext();

    // 2) reset Oversight stepper to step 1
    try {
        setOversightStep(OversightSteps.CANDIDATE_QUALITIES);
    } catch (_) {
        // ignore if stepper module isn't present
    }

    // 3) reset controllers UI+state
    resetHumanOversightUI();
    resetExtractedTripletsUI();

    // 4) clear file input (important: allow uploading SAME file again)
    const fileInput = document.getElementById(fileInputId);
    if (fileInput) {
        fileInput.value = ""; // this is the key for re-triggering "change"
        fileInput.blur();
    }

    // Optional: clear any lingering disabled state / tooltip
    // (usually our dropdown controller owns enabling/disabling)

    // 5) Hide the pipeline-porgress section if it exists (since the run is done)
    const progressSection = document.getElementById("pipeline-progress");
    if (progressSection) {
        progressSection.classList.add("d-none");
    }
}
