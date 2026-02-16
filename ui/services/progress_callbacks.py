from __future__ import annotations

"""
Progress callback helpers for long-running UI pipeline jobs.

We generate stage-bound callbacks so we don't repeat the same boilerplate
for every stage (KeyBERT, Decomposer, Similarity, Novelty, ...).
"""

from typing import Optional

from ui.services.job_store import JOB_STORE, JobProgressStage
# from ui.services.progress_types import ProgressCallback
from kbdebugger.types.ui import ProgressCallback

def make_job_progress_callback(*, job_id: str, stage: JobProgressStage) -> ProgressCallback:
    """
    Create a stage-bound progress callback for a specific job.

    The returned function matches our universal ProgressCallback signature:
        (current, total, message) -> None

    Parameters
    ----------
    job_id:
        ID of the job being tracked.
    stage:
        Human-readable stage label shown in the UI.

    Returns
    -------
    ProgressCallback
        Closure that writes progress into JOB_STORE.
    """

    def _cb(current: int, total: int, message: str) -> None:
        # Defensive normalization: keep UI stable even if caller sends weird values.
        cur = int(current) if current is not None else 0
        tot = int(total) if total is not None else 0

        # Never allow total=0 if progress is intended to be determinate.
        # If tot <= 0, we treat it as "indeterminate" by leaving it as None.
        JOB_STORE.update_progress(
            job_id,
            stage=stage,
            message=message,
            current=cur if total > 0 else None,
            total=tot if tot > 0 else None,
        )

    return _cb


def init_stage(
    *,
    job_id: str,
    stage: JobProgressStage,
    message: str,
    current: Optional[int] = None,
    total: Optional[int] = None,
) -> None:
    """
    Convenience helper to initialize a stage once before the loop starts.
    """
    JOB_STORE.update_progress(
        job_id,
        stage=stage,
        message=message,
        current=current,
        total=total,
    )
