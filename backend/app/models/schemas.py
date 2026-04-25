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
