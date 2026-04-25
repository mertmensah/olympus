from __future__ import annotations

import requests

from app.core.config import settings


class StorageService:
    def upload_bytes(self, file_key: str, content_type: str, payload: bytes) -> None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError("Supabase credentials are not configured.")

        upload_url = (
            f"{settings.supabase_url}/storage/v1/object/"
            f"{settings.supabase_bucket_name}/{file_key}"
        )

        headers = {
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "apikey": settings.supabase_service_role_key,
            "Content-Type": content_type,
            "x-upsert": "true",
        }

        response = requests.post(upload_url, data=payload, headers=headers, timeout=30)
        if response.status_code >= 400:
            raise RuntimeError(f"Supabase upload failed: {response.status_code} {response.text}")


storage_service = StorageService()
