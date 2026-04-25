from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.services.database import DATA_DIR, database

UPLOAD_ROOT = DATA_DIR / "uploads"


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(message: bytes) -> str:
    digest = hmac.new(settings.upload_token_secret.encode("utf-8"), message, hashlib.sha256).digest()
    return _b64url_encode(digest)


def create_upload_token(job_id: UUID, file_key: str, content_type: str) -> str:
    expires_at = int(datetime.now(timezone.utc).timestamp()) + settings.upload_token_ttl_seconds
    payload = {
        "job_id": str(job_id),
        "file_key": file_key,
        "content_type": content_type,
        "exp": expires_at,
    }
    message = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    encoded = _b64url_encode(message)
    signature = _sign(message)
    return f"{encoded}.{signature}"


def verify_upload_token(token: str) -> dict[str, Any]:
    try:
        encoded, provided_sig = token.split(".", 1)
    except ValueError as exc:
        raise ValueError("Invalid token format") from exc

    payload_bytes = _b64url_decode(encoded)
    expected_sig = _sign(payload_bytes)
    if not hmac.compare_digest(expected_sig, provided_sig):
        raise ValueError("Invalid token signature")

    payload = json.loads(payload_bytes.decode("utf-8"))
    now_ts = int(datetime.now(timezone.utc).timestamp())
    if now_ts > int(payload["exp"]):
        raise ValueError("Token expired")

    return payload


def store_uploaded_file(token_payload: dict[str, Any], body: bytes, content_type: str) -> tuple[str, int]:
    expected_content_type = token_payload["content_type"]
    if content_type != expected_content_type:
        raise ValueError("Content type mismatch")

    file_key = token_payload["file_key"]
    output_path = UPLOAD_ROOT / file_key
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(body)

    job_id = UUID(token_payload["job_id"])
    database.mark_asset_uploaded(job_id=job_id, file_key=file_key, size_bytes=len(body), storage_path=str(output_path))
    return file_key, len(body)
