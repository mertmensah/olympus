from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import UUID

import json

from app.models.schemas import ConnectionRecord, JobArtifact, JobCreateRequest, JobRecord, JobStatus, MediaSummary, SubjectRecord, SubjectRevision, UploadedAsset

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DB_PATH = DATA_DIR / "olympus.db"


class Database:
    def __init__(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        with self._lock:
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
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS job_artifacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS subjects (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL DEFAULT 'anonymous',
                    display_name TEXT NOT NULL DEFAULT '',
                    age INTEGER NOT NULL,
                    height_cm INTEGER NOT NULL,
                    generation INTEGER NOT NULL DEFAULT 0,
                    confidence REAL NOT NULL DEFAULT 0.0,
                    current_glb_key TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS user_connections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    requester_user_id TEXT NOT NULL,
                    target_user_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(requester_user_id, target_user_id)
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS subject_revisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id TEXT NOT NULL REFERENCES subjects(id),
                    job_id TEXT NOT NULL REFERENCES jobs(id),
                    glb_key TEXT NOT NULL,
                    quality_score REAL NOT NULL DEFAULT 0.0,
                    created_at TEXT NOT NULL
                )
                """
            )
            # Migrate existing jobs table: add subject_id if absent
            existing_cols = {row[1] for row in self._connection.execute("PRAGMA table_info(jobs)").fetchall()}
            if "subject_id" not in existing_cols:
                self._connection.execute("ALTER TABLE jobs ADD COLUMN subject_id TEXT REFERENCES subjects(id)")
            if "user_id" not in existing_cols:
                self._connection.execute("ALTER TABLE jobs ADD COLUMN user_id TEXT")

            subject_cols = {row[1] for row in self._connection.execute("PRAGMA table_info(subjects)").fetchall()}
            if "user_id" not in subject_cols:
                self._connection.execute("ALTER TABLE subjects ADD COLUMN user_id TEXT NOT NULL DEFAULT 'anonymous'")

            self._connection.commit()

    def create_job(
        self,
        job_id: UUID,
        payload: JobCreateRequest,
        subject_id: UUID | None = None,
        user_id: str | None = None,
    ) -> JobStatus:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO jobs (id, age, height_cm, photo_count, video_count, status, stage, created_at, subject_id, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    str(subject_id) if subject_id else None,
                    user_id,
                ),
            )
            self._connection.commit()
        return JobStatus(id=job_id, status="queued", stage="ingest")

    def get_job_status(self, job_id: UUID) -> JobStatus | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT id, status, stage FROM jobs WHERE id = ?",
                (str(job_id),),
            ).fetchone()
        if row is None:
            return None
        return JobStatus(id=UUID(row["id"]), status=row["status"], stage=row["stage"])

    def get_job_record(self, job_id: UUID) -> JobRecord | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT id, age, height_cm, photo_count, video_count, status, stage, created_at, subject_id, user_id
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
            subject_id=UUID(row["subject_id"]) if row["subject_id"] else None,
            user_id=row["user_id"],
        )

    def get_job_owner(self, job_id: UUID) -> str | None:
        with self._lock:
            row = self._connection.execute("SELECT user_id FROM jobs WHERE id = ?", (str(job_id),)).fetchone()
        if row is None:
            return None
        return row["user_id"]

    def update_job_state(self, job_id: UUID, status: str, stage: str) -> JobStatus | None:
        with self._lock:
            self._connection.execute(
                """
                UPDATE jobs
                SET status = ?, stage = ?
                WHERE id = ?
                """,
                (status, stage, str(job_id)),
            )
            self._connection.commit()
        return self.get_job_status(job_id)

    def reserve_asset(self, job_id: UUID, file_key: str, content_type: str, size_bytes: int) -> None:
        with self._lock:
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
        with self._lock:
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
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT file_key, content_type, size_bytes, status, uploaded_at, storage_path
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
                    storage_path=row["storage_path"],
                )
            )
        return assets

    def asset_counts(self, job_id: UUID) -> tuple[int, int]:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT
                    COUNT(*) AS total_count,
                    SUM(CASE WHEN status = 'uploaded' THEN 1 ELSE 0 END) AS uploaded_count
                FROM assets
                WHERE job_id = ?
                """,
                (str(job_id),),
            ).fetchone()
        if row is None:
            return (0, 0)
        return (int(row["total_count"] or 0), int(row["uploaded_count"] or 0))

    def save_job_artifact(self, job_id: UUID, stage: str, payload: dict) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO job_artifacts (job_id, stage, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (str(job_id), stage, json.dumps(payload), created_at),
            )
            self._connection.commit()

    def list_job_artifacts(self, job_id: UUID) -> list[JobArtifact]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT stage, payload_json, created_at
                FROM job_artifacts
                WHERE job_id = ?
                ORDER BY id ASC
                """,
                (str(job_id),),
            ).fetchall()

        artifacts: list[JobArtifact] = []
        for row in rows:
            artifacts.append(
                JobArtifact(
                    stage=row["stage"],
                    payload=json.loads(row["payload_json"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )
        return artifacts

    # ------------------------------------------------------------------
    # Subject methods
    # ------------------------------------------------------------------

    def create_subject(self, subject_id: UUID, user_id: str, display_name: str, age: int, height_cm: int) -> SubjectRecord:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO subjects (id, user_id, display_name, age, height_cm, generation, confidence, current_glb_key, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 0, 0.0, NULL, ?, ?)
                """,
                (str(subject_id), user_id, display_name, age, height_cm, now_iso, now_iso),
            )
            self._connection.commit()
        return self.get_subject(subject_id)  # type: ignore[return-value]

    def get_subject(self, subject_id: UUID) -> SubjectRecord | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT id, user_id, display_name, age, height_cm, generation, confidence, current_glb_key, created_at, updated_at FROM subjects WHERE id = ?",
                (str(subject_id),),
            ).fetchone()
        if row is None:
            return None
        return SubjectRecord(
            id=UUID(row["id"]),
            user_id=row["user_id"],
            display_name=row["display_name"],
            age=row["age"],
            height_cm=row["height_cm"],
            generation=row["generation"],
            confidence=row["confidence"],
            current_glb_key=row["current_glb_key"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def list_subjects(self, user_id: str | None = None) -> list[SubjectRecord]:
        with self._lock:
            if user_id:
                rows = self._connection.execute(
                    "SELECT id, user_id, display_name, age, height_cm, generation, confidence, current_glb_key, created_at, updated_at FROM subjects WHERE user_id = ? ORDER BY created_at DESC",
                    (user_id,),
                ).fetchall()
            else:
                rows = self._connection.execute(
                    "SELECT id, user_id, display_name, age, height_cm, generation, confidence, current_glb_key, created_at, updated_at FROM subjects ORDER BY created_at DESC"
                ).fetchall()
        return [
            SubjectRecord(
                id=UUID(row["id"]),
                user_id=row["user_id"],
                display_name=row["display_name"],
                age=row["age"],
                height_cm=row["height_cm"],
                generation=row["generation"],
                confidence=row["confidence"],
                current_glb_key=row["current_glb_key"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]

    def user_owns_subject(self, user_id: str, subject_id: UUID) -> bool:
        with self._lock:
            row = self._connection.execute(
                "SELECT 1 FROM subjects WHERE id = ? AND user_id = ?",
                (str(subject_id), user_id),
            ).fetchone()
        return row is not None

    def promote_subject_glb(self, subject_id: UUID, new_glb_key: str, quality_score: float) -> None:
        """Update the subject's current GLB and increment generation + confidence."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._lock:
            # Weighted rolling average: new confidence = 70% previous + 30% latest
            row = self._connection.execute(
                "SELECT confidence, generation FROM subjects WHERE id = ?",
                (str(subject_id),),
            ).fetchone()
            if row is None:
                return
            prev_confidence = float(row["confidence"])
            generation = int(row["generation"])
            new_confidence = round(prev_confidence * 0.7 + quality_score * 0.3, 2) if generation > 0 else round(quality_score, 2)
            self._connection.execute(
                """
                UPDATE subjects
                SET current_glb_key = ?, generation = ?, confidence = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_glb_key, generation + 1, new_confidence, now_iso, str(subject_id)),
            )
            self._connection.commit()

    def add_subject_revision(self, subject_id: UUID, job_id: UUID, glb_key: str, quality_score: float) -> SubjectRevision:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._lock:
            cursor = self._connection.execute(
                """
                INSERT INTO subject_revisions (subject_id, job_id, glb_key, quality_score, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(subject_id), str(job_id), glb_key, quality_score, now_iso),
            )
            self._connection.commit()
            revision_id = cursor.lastrowid
        return SubjectRevision(
            id=revision_id,
            subject_id=subject_id,
            job_id=job_id,
            glb_key=glb_key,
            quality_score=quality_score,
            created_at=datetime.fromisoformat(now_iso),
        )

    def list_subject_revisions(self, subject_id: UUID) -> list[SubjectRevision]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT id, subject_id, job_id, glb_key, quality_score, created_at FROM subject_revisions WHERE subject_id = ? ORDER BY id ASC",
                (str(subject_id),),
            ).fetchall()
        return [
            SubjectRevision(
                id=row["id"],
                subject_id=UUID(row["subject_id"]),
                job_id=UUID(row["job_id"]),
                glb_key=row["glb_key"],
                quality_score=row["quality_score"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Social connections
    # ------------------------------------------------------------------

    def create_connection_request(self, requester_user_id: str, target_user_id: str) -> ConnectionRecord:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._connection.execute(
                """
                INSERT OR IGNORE INTO user_connections (requester_user_id, target_user_id, status, created_at, updated_at)
                VALUES (?, ?, 'pending', ?, ?)
                """,
                (requester_user_id, target_user_id, now_iso, now_iso),
            )
            self._connection.commit()

            row = self._connection.execute(
                """
                SELECT id, requester_user_id, target_user_id, status, created_at, updated_at
                FROM user_connections
                WHERE requester_user_id = ? AND target_user_id = ?
                """,
                (requester_user_id, target_user_id),
            ).fetchone()

        return ConnectionRecord(
            id=row["id"],
            requester_user_id=row["requester_user_id"],
            target_user_id=row["target_user_id"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def list_connections_for_user(self, user_id: str) -> list[ConnectionRecord]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT id, requester_user_id, target_user_id, status, created_at, updated_at
                FROM user_connections
                WHERE requester_user_id = ? OR target_user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id, user_id),
            ).fetchall()
        return [
            ConnectionRecord(
                id=row["id"],
                requester_user_id=row["requester_user_id"],
                target_user_id=row["target_user_id"],
                status=row["status"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]

    def update_connection_status(self, connection_id: int, user_id: str, status: str) -> ConnectionRecord | None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._lock:
            row = self._connection.execute(
                "SELECT id, requester_user_id, target_user_id, status, created_at, updated_at FROM user_connections WHERE id = ?",
                (connection_id,),
            ).fetchone()
            if row is None:
                return None
            if row["target_user_id"] != user_id:
                return None

            self._connection.execute(
                "UPDATE user_connections SET status = ?, updated_at = ? WHERE id = ?",
                (status, now_iso, connection_id),
            )
            self._connection.commit()

            updated = self._connection.execute(
                "SELECT id, requester_user_id, target_user_id, status, created_at, updated_at FROM user_connections WHERE id = ?",
                (connection_id,),
            ).fetchone()

        return ConnectionRecord(
            id=updated["id"],
            requester_user_id=updated["requester_user_id"],
            target_user_id=updated["target_user_id"],
            status=updated["status"],
            created_at=datetime.fromisoformat(updated["created_at"]),
            updated_at=datetime.fromisoformat(updated["updated_at"]),
        )


database = Database()
