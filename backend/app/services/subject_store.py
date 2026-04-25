from __future__ import annotations

from uuid import UUID, uuid4

from app.models.schemas import SubjectCreateRequest, SubjectRecord, SubjectRevision
from app.services.database import database


class SubjectStore:
    def create(self, payload: SubjectCreateRequest) -> SubjectRecord:
        subject_id = uuid4()
        return database.create_subject(
            subject_id=subject_id,
            display_name=payload.display_name,
            age=payload.age,
            height_cm=payload.height_cm,
        )

    def get(self, subject_id: UUID) -> SubjectRecord | None:
        return database.get_subject(subject_id)

    def list_all(self) -> list[SubjectRecord]:
        return database.list_subjects()

    def list_revisions(self, subject_id: UUID) -> list[SubjectRevision]:
        return database.list_subject_revisions(subject_id)


subject_store = SubjectStore()
