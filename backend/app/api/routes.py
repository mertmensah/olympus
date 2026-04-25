from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import JobCreateRequest, JobRecord, JobStatus, UploadSessionRequest, UploadSessionResponse, UploadedAsset
from app.services.job_store import job_store
from app.services.upload_tokens import store_uploaded_file, verify_upload_token

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


@router.get("/jobs/{job_id}/record", response_model=JobRecord)
def get_job_record(job_id: UUID) -> JobRecord:
    job = job_store.get_record(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/upload-session", response_model=UploadSessionResponse)
def create_upload_session(job_id: UUID, payload: UploadSessionRequest) -> UploadSessionResponse:
    session = job_store.create_upload_session(job_id, payload)
    if not session:
        raise HTTPException(status_code=404, detail="Job not found")
    return session


@router.put("/uploads/{token}")
async def upload_file(token: str, request: Request) -> dict[str, str | int]:
    try:
        payload = verify_upload_token(token)
    except ValueError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error

    body = await request.body()
    content_type = request.headers.get("content-type", "application/octet-stream")

    try:
        file_key, size_bytes = store_uploaded_file(payload, body, content_type)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    return {"status": "uploaded", "file_key": file_key, "size_bytes": size_bytes}


@router.get("/jobs/{job_id}/assets", response_model=list[UploadedAsset])
def list_job_assets(job_id: UUID) -> list[UploadedAsset]:
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_store.list_assets(job_id)
