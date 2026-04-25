from uuid import UUID, uuid4

from app.models.schemas import JobCreateRequest, JobRecord, JobStatus, UploadSessionResponse, UploadTarget
from app.services.database import database


class JobStore:
    def create(self, payload: JobCreateRequest) -> JobStatus:
        job_id = uuid4()
        return database.create_job(job_id, payload)

    def get(self, job_id: UUID) -> JobStatus | None:
        return database.get_job_status(job_id)

    def get_record(self, job_id: UUID) -> JobRecord | None:
        return database.get_job_record(job_id)

    def create_upload_session(self, job_id: UUID) -> UploadSessionResponse | None:
        record = self.get_record(job_id)
        if record is None:
            return None

        targets: list[UploadTarget] = []

        for index in range(record.media_summary.photo_count):
            file_key = f"{job_id}/photos/photo-{index + 1:02d}.jpg"
            targets.append(
                UploadTarget(
                    file_key=file_key,
                    content_type="image/jpeg",
                    upload_url=f"https://storage.olympus.local/upload/{file_key}?token=dev",
                )
            )

        for index in range(record.media_summary.video_count):
            file_key = f"{job_id}/videos/video-{index + 1:02d}.mp4"
            targets.append(
                UploadTarget(
                    file_key=file_key,
                    content_type="video/mp4",
                    upload_url=f"https://storage.olympus.local/upload/{file_key}?token=dev",
                )
            )

        return UploadSessionResponse(job_id=job_id, expires_in_seconds=3600, targets=targets)


job_store = JobStore()
