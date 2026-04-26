from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.models.schemas import (
    AuthUser,
    ConnectionRecord,
    ConnectionRequestCreate,
    JobArtifact,
    JobCreateRequest,
    JobRecord,
    JobStatus,
    SubjectCreateRequest,
    SubjectRecord,
    SubjectRevision,
    UploadSessionRequest,
    UploadSessionResponse,
    UploadedAsset,
)
from app.services.auth import get_current_user
from app.services.database import database
from app.services.job_store import job_store
from app.services.storage_service import storage_service
from app.services.subject_store import subject_store
from app.services.upload_tokens import store_uploaded_file, verify_upload_token

router = APIRouter(prefix="/api", tags=["jobs"])
logger = logging.getLogger(__name__)


def _require_job_access(job_id: UUID, user_id: str) -> None:
    owner = database.get_job_owner(job_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if owner != user_id:
        raise HTTPException(status_code=403, detail="You do not have access to this job")


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/me", response_model=AuthUser)
def get_me(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    return user


@router.post("/jobs", response_model=JobStatus)
def create_job(payload: JobCreateRequest, user: AuthUser = Depends(get_current_user)) -> JobStatus:
    return job_store.create(payload, user_id=user.id)


@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: UUID, user: AuthUser = Depends(get_current_user)) -> JobStatus:
    _require_job_access(job_id, user.id)
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/record", response_model=JobRecord)
def get_job_record(job_id: UUID, user: AuthUser = Depends(get_current_user)) -> JobRecord:
    _require_job_access(job_id, user.id)
    job = job_store.get_record(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/upload-session", response_model=UploadSessionResponse)
def create_upload_session(job_id: UUID, payload: UploadSessionRequest, user: AuthUser = Depends(get_current_user)) -> UploadSessionResponse:
    _require_job_access(job_id, user.id)
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

    job_store.auto_start_if_ready(UUID(payload["job_id"]))

    return {"status": "uploaded", "file_key": file_key, "size_bytes": size_bytes}


@router.post("/jobs/{job_id}/start", response_model=JobStatus)
def start_job_pipeline(job_id: UUID, user: AuthUser = Depends(get_current_user)) -> JobStatus:
    _require_job_access(job_id, user.id)
    status = job_store.start_pipeline(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status


@router.get("/jobs/{job_id}/assets", response_model=list[UploadedAsset])
def list_job_assets(job_id: UUID, user: AuthUser = Depends(get_current_user)) -> list[UploadedAsset]:
    _require_job_access(job_id, user.id)
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_store.list_assets(job_id)


@router.get("/jobs/{job_id}/artifacts", response_model=list[JobArtifact])
def list_job_artifacts(job_id: UUID, user: AuthUser = Depends(get_current_user)) -> list[JobArtifact]:
    _require_job_access(job_id, user.id)
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job_store.list_artifacts(job_id)


@router.get("/jobs/{job_id}/reconstruction")
def get_reconstruction_file(job_id: UUID, user: AuthUser = Depends(get_current_user)) -> Response:
    _require_job_access(job_id, user.id)
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    artifacts = job_store.list_artifacts(job_id)
    reconstruct = next((a for a in reversed(artifacts) if a.stage == "reconstruct"), None)
    if reconstruct is None:
        raise HTTPException(status_code=404, detail="Reconstruct artifact not found")

    output_asset_key = reconstruct.payload.get("output_asset_key")
    if not output_asset_key:
        raise HTTPException(status_code=404, detail="Reconstruction output key missing")

    content_type = reconstruct.payload.get("runtime", {}).get("content_type", "application/octet-stream")
    if content_type != "model/gltf-binary":
        raise HTTPException(
            status_code=409,
            detail=(
                "Reconstruction output is not a GLB model. "
                f"Found content_type={content_type}. "
                "Run a new job after restarting backend with latest adapter code."
            ),
        )

    try:
        payload = storage_service.download_bytes(output_asset_key)
    except Exception as exc:
        logger.exception("Failed to download reconstruction output", extra={"job_id": str(job_id), "file_key": output_asset_key})
        raise HTTPException(status_code=500, detail=f"Failed to download reconstruction output: {exc}") from exc

    logger.info(
        "Serving reconstruction output",
        extra={
            "job_id": str(job_id),
            "file_key": output_asset_key,
            "bytes": len(payload),
            "content_type": content_type,
        },
    )
    return Response(content=payload, media_type=content_type)


@router.get("/jobs/{job_id}/debug")
def get_job_debug(job_id: UUID, user: AuthUser = Depends(get_current_user)) -> dict:
    _require_job_access(job_id, user.id)
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    assets = job_store.list_assets(job_id)
    artifacts = job_store.list_artifacts(job_id)
    reconstruct = next((a for a in reversed(artifacts) if a.stage == "reconstruct"), None)
    file_key = reconstruct.payload.get("output_asset_key") if reconstruct else None

    storage_probe = {"ok": False, "size_bytes": 0, "error": None}
    if file_key:
        try:
            blob = storage_service.download_bytes(file_key)
            storage_probe = {"ok": True, "size_bytes": len(blob), "error": None}
        except Exception as exc:
            storage_probe = {"ok": False, "size_bytes": 0, "error": str(exc)}

    return {
        "job": {"id": str(job_id), "status": job.status, "stage": job.stage},
        "assets": {
            "count": len(assets),
            "uploaded": sum(1 for a in assets if a.status == "uploaded"),
        },
        "artifacts": [
            {
                "stage": a.stage,
                "created_at": a.created_at.isoformat(),
                "payload_keys": sorted(a.payload.keys()),
            }
            for a in artifacts
        ],
        "reconstruction": {
            "has_artifact": reconstruct is not None,
            "output_asset_key": file_key,
            "runtime": reconstruct.payload.get("runtime") if reconstruct else None,
            "adapter": reconstruct.payload.get("adapter") if reconstruct else None,
        },
        "storage_probe": storage_probe,
    }


@router.get("/jobs/{job_id}/input-feedback")
def get_job_input_feedback(job_id: UUID, user: AuthUser = Depends(get_current_user)) -> dict:
    _require_job_access(job_id, user.id)
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    artifacts = job_store.list_artifacts(job_id)
    quality = next((a for a in reversed(artifacts) if a.stage == "quality"), None)
    reconstruct = next((a for a in reversed(artifacts) if a.stage == "reconstruct"), None)

    if quality is None:
        raise HTTPException(status_code=404, detail="Quality artifact not found yet")

    feedback = quality.payload.get("input_feedback", {})
    per_input = feedback.get("per_input", [])
    selected_assets = set(reconstruct.payload.get("selected_assets", [])) if reconstruct else set()

    enriched = []
    for item in per_input:
        file_key = item.get("file_key", "")
        enriched.append(
            {
                **item,
                "used_for_reconstruction": file_key in selected_assets,
            }
        )

    return {
        "job": {
            "id": str(job_id),
            "status": job.status,
            "stage": job.stage,
        },
        "summary": feedback.get("summary", {}),
        "global_recommendations": feedback.get("global_recommendations", []),
        "per_input": enriched,
        "selected_asset_count": len(selected_assets),
    }


# -----------------------------------------------------------------------
# Subject routes
# -----------------------------------------------------------------------

@router.post("/subjects", response_model=SubjectRecord, status_code=201)
def create_subject(payload: SubjectCreateRequest, user: AuthUser = Depends(get_current_user)) -> SubjectRecord:
    return subject_store.create(user.id, payload)


@router.get("/subjects", response_model=list[SubjectRecord])
def list_subjects(user: AuthUser = Depends(get_current_user)) -> list[SubjectRecord]:
    return subject_store.list_all(user.id)


@router.get("/subjects/{subject_id}", response_model=SubjectRecord)
def get_subject(subject_id: UUID, user: AuthUser = Depends(get_current_user)) -> SubjectRecord:
    subject = subject_store.get(subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    if subject.user_id != user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this subject")
    return subject


@router.get("/subjects/{subject_id}/revisions", response_model=list[SubjectRevision])
def list_subject_revisions(subject_id: UUID, user: AuthUser = Depends(get_current_user)) -> list[SubjectRevision]:
    subject = subject_store.get(subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    if subject.user_id != user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this subject")
    return subject_store.list_revisions(subject_id)


@router.post("/subjects/{subject_id}/jobs", response_model=JobStatus, status_code=201)
def create_job_for_subject(subject_id: UUID, payload: JobCreateRequest, user: AuthUser = Depends(get_current_user)) -> JobStatus:
    """Create a new refinement job linked to an existing subject."""
    if not subject_store.owns_subject(user.id, subject_id):
        raise HTTPException(status_code=404, detail="Subject not found")
    return job_store.create(payload, user_id=user.id, subject_id=subject_id)


@router.get("/subjects/{subject_id}/reconstruction")
def get_subject_reconstruction(subject_id: UUID, user: AuthUser = Depends(get_current_user)) -> Response:
    """Serve the subject's current best GLB directly."""
    subject = subject_store.get(subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    if subject.user_id != user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this subject")
    if not subject.current_glb_key:
        raise HTTPException(status_code=404, detail="Subject has no reconstruction yet — submit a job first")
    try:
        glb_bytes = storage_service.download_bytes(subject.current_glb_key)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to download subject GLB: {exc}") from exc
    return Response(content=glb_bytes, media_type="model/gltf-binary")


@router.post("/connections/request", response_model=ConnectionRecord, status_code=201)
def request_connection(payload: ConnectionRequestCreate, user: AuthUser = Depends(get_current_user)) -> ConnectionRecord:
    if payload.target_user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot connect to yourself")
    return database.create_connection_request(user.id, payload.target_user_id)


@router.get("/connections", response_model=list[ConnectionRecord])
def list_connections(user: AuthUser = Depends(get_current_user)) -> list[ConnectionRecord]:
    return database.list_connections_for_user(user.id)


@router.post("/connections/{connection_id}/accept", response_model=ConnectionRecord)
def accept_connection(connection_id: int, user: AuthUser = Depends(get_current_user)) -> ConnectionRecord:
    record = database.update_connection_status(connection_id, user.id, "accepted")
    if record is None:
        raise HTTPException(status_code=404, detail="Connection request not found")
    return record


@router.post("/connections/{connection_id}/decline", response_model=ConnectionRecord)
def decline_connection(connection_id: int, user: AuthUser = Depends(get_current_user)) -> ConnectionRecord:
    record = database.update_connection_status(connection_id, user.id, "declined")
    if record is None:
        raise HTTPException(status_code=404, detail="Connection request not found")
    return record
