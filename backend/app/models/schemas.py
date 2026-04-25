from datetime import datetime
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
