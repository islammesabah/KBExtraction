from __future__ import annotations
from typing import List

"""
Pipeline API routes.

Responsibilities
---------------
- Accept uploads and start background pipeline jobs.
- Expose job status for polling.

Notes
-----
Flask is the server. Our 'kbdebugger' code runs *inside* Flask
in the background job thread.
"""

from pathlib import Path
from threading import Thread

from flask import Blueprint, jsonify, request

from kbdebugger.pipeline.config import PipelineConfig

from ui.services.job_store import JOB_STORE
from ui.services.pipeline_runner import run_pipeline
from ui.services.pipeline_config_service import get_pipeline_config

from kbdebugger.novelty.utils import coerce_from_browser_dict
from kbdebugger.novelty.types import QualityNoveltyInput, QualityNoveltyResult
from kbdebugger.extraction.triplet_extraction_batch import extract_triplets_from_novelty_results, extract_triplets_batch

pipeline_bp = Blueprint("pipeline", __name__)


def _save_upload_to_tmp(file_storage) -> Path:
    """
    Save uploaded file to a temporary location under ui/temp_uploads/.

    Returns
    -------
    Path
        Filesystem path to the saved upload.
    """
    uploads_dir = Path("ui/temp_uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)

    # Keep original name; we can sanitize further if needed.
    dst = uploads_dir / file_storage.filename
    file_storage.save(dst)
    return dst


@pipeline_bp.post("/run")
def start_pipeline_run():
    """
    Start a long-running pipeline job (Stage 2 for now).

    Request
    -------
    multipart/form-data:
        document: File
    query:
        keyword: str

    Response
    --------
    JSON:
        {"job_id": "<uuid>"}
    """
    keyword = (request.args.get("keyword") or "").strip()
    if not keyword:
        return jsonify({"error": "Missing query param: keyword"}), 400

    if "document" not in request.files:
        return jsonify({"error": "Missing file part: document"}), 400

    file = request.files["document"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    job = JOB_STORE.create_job()
    path = _save_upload_to_tmp(file)

    cfg = get_pipeline_config()

    def worker() -> None:
        try:
            result = run_pipeline(job_id=job.job_id, file_path=path, keyword=keyword, cfg=cfg)
            JOB_STORE.set_done(job.job_id, result)
        except Exception as e:
            JOB_STORE.set_error(job.job_id, str(e))

    # Fire a thread in the background 
    # then return an immediate response with the job_id
    # so that the other GET API can keep polling the status of this job
    Thread(target=worker, daemon=True).start()

    return jsonify({"job_id": job.job_id})


@pipeline_bp.get("/jobs/<job_id>")
def get_job_status(job_id: str):
    """
    Poll job status.

    Returns
    -------
    JSON
        {
          "state": "...",
          "stage": "...",
          "message": "...",
          "progress": {"current": ..., "total": ...},
          "result": {...} | null,
          "error": "..." | null
        }
    """
    rec = JOB_STORE.get(job_id)
    if rec is None:
        return jsonify({"error": f"Unknown job_id: {job_id}"}), 404

    return jsonify(
        {
            "state": rec.state,
            "stage": rec.progress.stage,
            "message": rec.progress.message,
            "progress": {"current": rec.progress.current, "total": rec.progress.total},
            "result": rec.result,
            "error": rec.error,
            "started_at": rec.started_at
        }
    )


@pipeline_bp.post("/triplet-extraction")
def start_triplet_extraction():
    """
    Start Stage 6 (Triplet extraction) as a background job.

    Request (JSON)
    --------------
    {
        "selected_results": [ <QualityNoveltyResult-like dict>, ... ]
    }

    Response (JSON)
    ---------------
    { "job_id": "<uuid>" }

    Notes
    -----
    Client should poll GET /api/pipeline/jobs/<job_id> to retrieve:
    - progress updates (optional later)
    - final result: List[ExtractionResult]
    """
    payload = request.get_json(silent=True) or {}
    raw = payload.get("selected_qualities")

    if not isinstance(raw, list) or len(raw) == 0:
        return jsonify({"error": "Expected JSON body with non-empty 'selected_qualities' list"}), 400

    # sanitize
    qualities = [str(x).strip() for x in raw if x is not None and str(x).strip()]
    
    if not qualities:
        return jsonify({"error": "No non-empty qualities provided."}), 400
    
    job = JOB_STORE.create_job()

    def worker() -> None:
        try:
            # Stage 6
            JOB_STORE.set_running(job.job_id)
            JOB_STORE.update_progress(
                job.job_id,
                stage="TripletExtractionLLM",
                message=f"🧬 Extracting triplets from {len(qualities)} selected qualities...",
                current=None,
                total=None,
            )
            
            cfg = get_pipeline_config()

            extracted = extract_triplets_batch(
                qualities,
                batch_size=cfg.triplet_extraction_batch_size,  # or just hardcode to 5 for now
            )

            result = {
                "extracted_triplets": extracted,
            }

            # Store result for polling endpoint
            JOB_STORE.set_done(job.job_id, result)
        except Exception as e:
            JOB_STORE.set_error(job.job_id, str(e))

    Thread(target=worker, daemon=True).start()
    return jsonify({"job_id": job.job_id})
