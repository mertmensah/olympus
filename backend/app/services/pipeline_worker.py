from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from uuid import UUID

from app.services.database import database
from app.services.pipeline_stages import (
    run_deliver_stage,
    run_ingest_stage,
    run_postprocess_stage,
    run_quality_stage,
    run_reconstruct_stage,
)


class PipelineWorker:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="olympus-pipeline")
        self._active_jobs: set[UUID] = set()
        self._lock = Lock()

    def enqueue(self, job_id: UUID) -> bool:
        with self._lock:
            if job_id in self._active_jobs:
                return False
            self._active_jobs.add(job_id)

        self._executor.submit(self._run_pipeline, job_id)
        return True

    def _run_pipeline(self, job_id: UUID) -> None:
        current_stage = "ingest"
        try:
            self._set_state(job_id, "processing", "ingest")
            database.save_job_artifact(job_id, "ingest", run_ingest_stage(job_id))

            current_stage = "quality"
            self._set_state(job_id, "processing", "quality")
            database.save_job_artifact(job_id, "quality", run_quality_stage(job_id))

            current_stage = "reconstruct"
            self._set_state(job_id, "processing", "reconstruct")
            database.save_job_artifact(job_id, "reconstruct", run_reconstruct_stage(job_id))

            current_stage = "postprocess"
            self._set_state(job_id, "processing", "postprocess")
            database.save_job_artifact(job_id, "postprocess", run_postprocess_stage(job_id))

            current_stage = "deliver"
            database.save_job_artifact(job_id, "deliver", run_deliver_stage(job_id))

            self._set_state(job_id, "completed", "deliver")
        except Exception:
            self._set_state(job_id, "failed", current_stage)
        finally:
            with self._lock:
                self._active_jobs.discard(job_id)

    @staticmethod
    def _set_state(job_id: UUID, status: str, stage: str) -> None:
        database.update_job_state(job_id=job_id, status=status, stage=stage)


pipeline_worker = PipelineWorker()
