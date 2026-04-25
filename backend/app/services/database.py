from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from app.models.schemas import JobCreateRequest, JobRecord, JobStatus, MediaSummary, UploadedAsset

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
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                file_key TEXT NOT NULL,
                content_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                status TEXT NOT NULL,
                uploaded_at TEXT,
                storage_path TEXT,
                UNIQUE(job_id, file_key)
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

    def reserve_asset(self, job_id: UUID, file_key: str, content_type: str, size_bytes: int) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO assets (job_id, file_key, content_type, size_bytes, status, uploaded_at, storage_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (str(job_id), file_key, content_type, size_bytes, "pending", None, None),
        )
        self._connection.commit()

    def mark_asset_uploaded(self, job_id: UUID, file_key: str, size_bytes: int, storage_path: str) -> None:
        uploaded_at = datetime.now(timezone.utc).isoformat()
        self._connection.execute(
            """
            UPDATE assets
            SET size_bytes = ?, status = ?, uploaded_at = ?, storage_path = ?
            WHERE job_id = ? AND file_key = ?
            """,
            (size_bytes, "uploaded", uploaded_at, storage_path, str(job_id), file_key),
        )
        self._connection.commit()

    def list_assets(self, job_id: UUID) -> list[UploadedAsset]:
        rows = self._connection.execute(
            """
            SELECT file_key, content_type, size_bytes, status, uploaded_at
            FROM assets
            WHERE job_id = ?
            ORDER BY id ASC
            """,
            (str(job_id),),
        ).fetchall()

        assets: list[UploadedAsset] = []
        for row in rows:
            assets.append(
                UploadedAsset(
                    file_key=row["file_key"],
                    content_type=row["content_type"],
                    size_bytes=row["size_bytes"],
                    status=row["status"],
                    uploaded_at=datetime.fromisoformat(row["uploaded_at"]) if row["uploaded_at"] else None,
                )
            )
        return assets


database = Database()
