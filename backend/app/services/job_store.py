from uuid import UUID, uuid4

from app.core.config import settings
from app.models.schemas import JobCreateRequest, JobRecord, JobStatus, UploadSessionRequest, UploadSessionResponse, UploadTarget
from app.services.database import database
from app.services.pipeline_worker import pipeline_worker
from app.services.upload_tokens import create_upload_token


class JobStore:
    def create(self, payload: JobCreateRequest, user_id: str | None = None, subject_id: UUID | None = None) -> JobStatus:
        job_id = uuid4()
        return database.create_job(job_id, payload, subject_id=subject_id, user_id=user_id)

    def get(self, job_id: UUID) -> JobStatus | None:
        return database.get_job_status(job_id)

    def get_record(self, job_id: UUID) -> JobRecord | None:
        return database.get_job_record(job_id)

    def create_upload_session(self, job_id: UUID, payload: UploadSessionRequest) -> UploadSessionResponse | None:
        record = self.get_record(job_id)
        if record is None:
            return None

        targets: list[UploadTarget] = []
        counters = {"photo": 0, "video": 0, "audio": 0}

        for file in payload.files:
            counters[file.kind] += 1
            extension = self._extension_from_content_type(file.content_type)
            file_key = f"{job_id}/{file.kind}s/{file.kind}-{counters[file.kind]:02d}.{extension}"
            token = create_upload_token(job_id=job_id, file_key=file_key, content_type=file.content_type)
            database.reserve_asset(job_id=job_id, file_key=file_key, content_type=file.content_type, size_bytes=file.size_bytes)

            targets.append(
                UploadTarget(
                    client_id=file.client_id,
                    file_key=file_key,
                    content_type=file.content_type,
                    method="PUT",
                    upload_url=f"{settings.api_public_base_url}/api/uploads/{token}",
                )
            )

        return UploadSessionResponse(job_id=job_id, expires_in_seconds=settings.upload_token_ttl_seconds, targets=targets)

    def list_assets(self, job_id: UUID):
        return database.list_assets(job_id)

    def list_artifacts(self, job_id: UUID):
        return database.list_job_artifacts(job_id)

    def start_pipeline(self, job_id: UUID) -> JobStatus | None:
        status = self.get(job_id)
        if status is None:
            return None

        total_assets, uploaded_assets = database.asset_counts(job_id)
        if total_assets == 0 or uploaded_assets < total_assets:
            return status

        if status.status == "completed":
            return status

        started = pipeline_worker.enqueue(job_id)
        if started:
            return database.update_job_state(job_id=job_id, status="processing", stage="ingest")
        return self.get(job_id)

    def auto_start_if_ready(self, job_id: UUID) -> bool:
        status = self.get(job_id)
        if status is None:
            return False

        if status.status in {"processing", "completed"}:
            return False

        total_assets, uploaded_assets = database.asset_counts(job_id)
        if total_assets == 0 or uploaded_assets < total_assets:
            return False

        started = pipeline_worker.enqueue(job_id)
        if started:
            database.update_job_state(job_id=job_id, status="processing", stage="ingest")
        return started

    @staticmethod
    def _extension_from_content_type(content_type: str) -> str:
        mapping = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "video/mp4": "mp4",
            "audio/wav": "wav",
            "audio/mpeg": "mp3",
        }
        return mapping.get(content_type, "bin")


job_store = JobStore()
