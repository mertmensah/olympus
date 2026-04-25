from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import sleep
from uuid import UUID

from app.services.database import database


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
        try:
            self._set_state(job_id, "processing", "ingest")
            sleep(1)

            self._set_state(job_id, "processing", "quality")
            sleep(1)

            self._set_state(job_id, "processing", "reconstruct")
            sleep(2)

            self._set_state(job_id, "processing", "postprocess")
            sleep(1)

            self._set_state(job_id, "completed", "deliver")
        except Exception:
            self._set_state(job_id, "failed", "ingest")
        finally:
            with self._lock:
                self._active_jobs.discard(job_id)

    @staticmethod
    def _set_state(job_id: UUID, status: str, stage: str) -> None:
        database.update_job_state(job_id=job_id, status=status, stage=stage)


pipeline_worker = PipelineWorker()
