from typing import Dict
from uuid import UUID, uuid4

from app.models.schemas import JobCreateRequest, JobStatus


class JobStore:
    def __init__(self) -> None:
        self._jobs: Dict[UUID, JobStatus] = {}

    def create(self, payload: JobCreateRequest) -> JobStatus:
        job_id = uuid4()
        job = JobStatus(id=job_id, status="queued", stage="ingest")
        self._jobs[job_id] = job
        return job

    def get(self, job_id: UUID) -> JobStatus | None:
        return self._jobs.get(job_id)


job_store = JobStore()
