from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from app.models.schemas import JobCreateRequest, JobRecord, JobStatus, MediaSummary

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DB_PATH = DATA_DIR / "olympus.db"


class Database:
    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                age INTEGER NOT NULL,
                height_cm INTEGER NOT NULL,
                photo_count INTEGER NOT NULL,
                video_count INTEGER NOT NULL,
                status TEXT NOT NULL,
                stage TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def create_job(self, job_id: UUID, payload: JobCreateRequest) -> JobStatus:
        now_iso = datetime.now(timezone.utc).isoformat()
        self._connection.execute(
            """
            INSERT INTO jobs (id, age, height_cm, photo_count, video_count, status, stage, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(job_id),
                payload.age,
                payload.height_cm,
                payload.media_summary.photo_count,
                payload.media_summary.video_count,
                "queued",
                "ingest",
                now_iso,
            ),
        )
        self._connection.commit()
        return JobStatus(id=job_id, status="queued", stage="ingest")

    def get_job_status(self, job_id: UUID) -> JobStatus | None:
        row = self._connection.execute(
            "SELECT id, status, stage FROM jobs WHERE id = ?",
            (str(job_id),),
        ).fetchone()
        if row is None:
            return None
        return JobStatus(id=UUID(row["id"]), status=row["status"], stage=row["stage"])

    def get_job_record(self, job_id: UUID) -> JobRecord | None:
        row = self._connection.execute(
            """
            SELECT id, age, height_cm, photo_count, video_count, status, stage, created_at
            FROM jobs
            WHERE id = ?
            """,
            (str(job_id),),
        ).fetchone()
        if row is None:
            return None

        return JobRecord(
            id=UUID(row["id"]),
            age=row["age"],
            height_cm=row["height_cm"],
            media_summary=MediaSummary(photo_count=row["photo_count"], video_count=row["video_count"]),
            status=row["status"],
            stage=row["stage"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )


database = Database()
