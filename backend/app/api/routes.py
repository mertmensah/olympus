from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.models.schemas import JobCreateRequest, JobStatus
from app.services.job_store import job_store

router = APIRouter(prefix="/api", tags=["jobs"])


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/jobs", response_model=JobStatus)
def create_job(payload: JobCreateRequest) -> JobStatus:
    return job_store.create(payload)


@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: UUID) -> JobStatus:
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
