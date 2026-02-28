/**
 * Oversight Stepper
 * -----------------
 * Centralizes the "two-step" Oversight flow:
 *   Step 1: Candidate sentences (novelty results)
 *   Step 2: Extracted triplets review + KG upsert
 *
 * Responsibilities
 * ---------------
 * - Show/hide the correct DOM sections for the current step.
 * - Update the Oversight header title + helper text consistently.
 *
 * This prevents duplication across controllers and keeps transitions robust.
 */

const DEFAULT_TITLE = "Oversight";

/**
 * Update the Oversight header title + helper text.
 *
 * @param {Object} params
 * @param {string} params.title Main H2 title text.
 * @param {string} params.helper Helper description shown under the title.
 */
export function setOversightHeader({ title, helper }) {
    const titleEl = document.getElementById("oversight-title");
    const helperEl = document.getElementById("oversight-helper");

    if (titleEl) titleEl.textContent = title || DEFAULT_TITLE;
    if (helperEl) helperEl.textContent = helper || "";
}


/**
 * @typedef {"candidate-qualities" | "triplets-review"} OversightStep
 */

/**
 * Titles + helper texts per step.
 * Keep strings here so controllers never hardcode UI copy.
 */
const STEP_COPY = {
    "candidate-qualities": {
        title: "💬 Candidate Sentences",
        helper:
            "KBDebugger extracted and classified these quality sentences by comparing them to the current Knowledge Graph. Your decision is decisive 🧑🏻‍⚖️ Please select the sentences you would like to proceed with.",
    },
    "triplets-review": {
        title: "🧬 Extracted Triplets",
        helper: "Review, edit, or delete triplets before inserting into the Knowledge Graph.",
    },
};

/**
 * Show/hide candidate qualities UI.
 * In our markup this is `.oversight-top`.
 */
function setShowCandidateQualitiesSection(show) {
    const section = document.querySelector(".oversight-top");
    if (!section) return;
    section.classList.toggle("d-none", !show);
}

/**
 * Show/hide extracted triplets review UI.
 * In our markup this is `#oversight-bottom`.
 */
function setShowExtractedTripletsSection(show) {
    const section = document.getElementById("oversight-bottom");
    if (!section) return;
    section.classList.toggle("d-none", !show);
}

/**
 * Set Oversight step (single source of truth).
 *
 * @param {OversightStep} step
 */
export function setOversightStep(step) {
    if (step === "candidate-qualities") {
        setShowCandidateQualitiesSection(true);
        setShowExtractedTripletsSection(false);
    } else if (step === "triplets-review") {
        setShowCandidateQualitiesSection(false);
        setShowExtractedTripletsSection(true);
    } else {
        // Defensive: unknown step -> fall back to candidate step
        setShowCandidateQualitiesSection(true);
        setShowExtractedTripletsSection(false);
        step = "candidate-qualities";
    }

    const copy = STEP_COPY[step];
    setOversightHeader({
        title: copy?.title ?? "Oversight",
        helper: copy?.helper ?? "",
    });
}

/**
 * Optional convenience helpers.
 */
export const OversightSteps = Object.freeze({
    CANDIDATE_SENTENCES: "candidate-qualities",
    EXTRACTED_TRIPLETS: "triplets-review",
});
