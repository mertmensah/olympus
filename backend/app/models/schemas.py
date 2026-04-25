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
    file_key: str
    content_type: Literal["image/jpeg", "image/png", "video/mp4"]
    upload_url: str


class UploadSessionResponse(BaseModel):
    job_id: UUID
    expires_in_seconds: int
    targets: list[UploadTarget]
