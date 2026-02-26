from __future__ import annotations

from kbdebugger.utils.time import now_utc_iso

"""
In-memory job store for long-running pipeline tasks.

Why in-memory?
--------------
- Fast to implement for research prototypes.
- No external dependencies (Redis/Celery) while we're iterating.

Caveats
-------
- Jobs are lost if the Flask process restarts.
- Not suitable for multi-worker deployments.

Upgrade path
------------
Replace internals with Redis/Celery later without changing route contracts.
"""

from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Dict, Literal, Optional
from uuid import uuid4
from time import time

# Define a Literal for stage:
JobProgressStage = Literal[
    "Queued", 
    "Done",
    "Error",
    
    "Docling", # 2a
    "KeyBERT", # 2b
    "DecomposerLLM", # 2c
    "SubgraphSimilarity", # 3
    "NoveltyLLM", # 4
    "TripletExtractionLLM", # 5
    "KnowledgeGraphUpsert", # 6
]

JobState = Literal[
    "queued",
    "running",
    "done",
    "error"
]

@dataclass
class JobProgress:
    """
    Progress state for a job.

    Attributes
    ----------
    stage:
        Short machine-friendly stage id (e.g., "docling", "keybert", "decomposer").
    message:
        Human-friendly status message shown in UI.
    current:
        Current progress value (optional).
    total:
        Total progress value (optional).
    """
    # stage: str = "queued"
    stage: JobProgressStage = "Queued"
    message: str = "Queued."
    current: Optional[int] = None
    total: Optional[int] = None


@dataclass
class JobRecord:
    """
    Full job record tracked by the UI.

    state:
        One of: "queued", "running", "done", "error"
    result:
        JSON-serializable payload returned once complete.
    error:
        Error message if state == "error".
    """
    job_id: str
    started_at: float = field(default_factory=time)
    state: JobState = "queued"
    progress: JobProgress = field(default_factory=JobProgress)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class InMemoryJobStore:
    """
    Thread-safe in-memory job registry.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._jobs: Dict[str, JobRecord] = {}

    def create_job(self) -> JobRecord:
        """
        Create and register a new job.

        Returns
        -------
        JobRecord
            Newly created job record.
        """
        job_id = uuid4().hex
        rec = JobRecord(job_id=job_id)
        with self._lock:
            self._jobs[job_id] = rec
        return rec

    def get(self, job_id: str) -> Optional[JobRecord]:
        """
        Retrieve a job record (or None if missing).
        """
        with self._lock:
            return self._jobs.get(job_id)

    def set_running(self, job_id: str) -> None:
        with self._lock:
            rec = self._jobs[job_id]
            rec.state = "running"

            # only set once per run
            if not rec.started_at:
                rec.started_at = now_utc_iso()


    def set_done(self, job_id: str, result: Dict[str, Any]) -> None:
        with self._lock:
            rec = self._jobs[job_id]
            rec.state = "done"
            rec.result = result
            rec.progress = JobProgress(stage="Done", message="✅ Completed.", current=1, total=1)

    def set_error(self, job_id: str, error: str) -> None:
        with self._lock:
            rec = self._jobs[job_id]
            rec.state = "error"
            rec.error = error
            rec.progress = JobProgress(stage="Error", message="❌ Failed.", current=None, total=None)

    def update_progress(
        self,
        job_id: str,
        *,
        stage: JobProgressStage,
        message: str,
        current: Optional[int] = None,
        total: Optional[int] = None,
    ) -> None:
        """
        Update the job's progress fields.

        This is designed to be called frequently from a background worker.
        """
        with self._lock:
            rec = self._jobs[job_id]
            rec.progress.stage = stage
            rec.progress.message = message
            rec.progress.current = current
            rec.progress.total = total


# Global singleton for now (simple).
JOB_STORE = InMemoryJobStore()
