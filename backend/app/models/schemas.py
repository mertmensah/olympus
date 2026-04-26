from datetime import datetime
from typing import Any
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class MediaSummary(BaseModel):
    photo_count: int = Field(ge=1, le=100)
    video_count: int = Field(ge=0, le=20)


class JobCreateRequest(BaseModel):
    age: int = Field(ge=13, le=120)
    height_cm: int = Field(ge=80, le=260)
    media_summary: MediaSummary


class JobStatus(BaseModel):
    id: UUID
    status: Literal["queued", "processing", "completed", "failed"]
    stage: Literal["ingest", "quality", "reconstruct", "postprocess", "deliver"]


class JobRecord(JobStatus):
    age: int = Field(ge=13, le=120)
    height_cm: int = Field(ge=80, le=260)
    media_summary: MediaSummary
    created_at: datetime
    subject_id: UUID | None = None
    user_id: str | None = None


class UploadTarget(BaseModel):
    client_id: str
    file_key: str
    content_type: str
    method: Literal["PUT"] = "PUT"
    upload_url: str


class UploadFileDescriptor(BaseModel):
    client_id: str
    kind: Literal["photo", "video", "audio"]
    file_name: str
    content_type: str
    size_bytes: int = Field(ge=1)


class UploadSessionRequest(BaseModel):
    files: list[UploadFileDescriptor] = Field(min_length=1)


class UploadSessionResponse(BaseModel):
    job_id: UUID
    expires_in_seconds: int
    targets: list[UploadTarget]


class UploadedAsset(BaseModel):
    file_key: str
    content_type: str
    size_bytes: int
    status: Literal["pending", "uploaded"]
    uploaded_at: datetime | None = None
    storage_path: str | None = None


class JobArtifact(BaseModel):
    stage: Literal["ingest", "quality", "reconstruct", "postprocess", "deliver"]
    payload: dict[str, Any]
    created_at: datetime


class SubjectCreateRequest(BaseModel):
    display_name: str = Field(default="", max_length=120)
    age: int = Field(ge=13, le=120)
    height_cm: int = Field(ge=80, le=260)


class SubjectRecord(BaseModel):
    id: UUID
    user_id: str
    display_name: str
    age: int
    height_cm: int
    generation: int          # how many successful jobs have improved this subject
    confidence: float        # rolling quality score (0–100)
    current_glb_key: str | None = None
    created_at: datetime
    updated_at: datetime


class SubjectRevision(BaseModel):
    id: int
    subject_id: UUID
    job_id: UUID
    glb_key: str
    quality_score: float
    created_at: datetime


class AuthUser(BaseModel):
    id: str
    email: str | None = None


class ConnectionRequestCreate(BaseModel):
    target_email: str | None = Field(default=None, min_length=3, max_length=254)
    target_user_id: str | None = Field(default=None, min_length=3, max_length=128)


class ConnectionRecord(BaseModel):
    id: int
    requester_user_id: str
    target_user_id: str
    requester_email: str | None = None
    target_email: str | None = None
    status: Literal["pending", "accepted", "declined"]
    created_at: datetime
    updated_at: datetime
