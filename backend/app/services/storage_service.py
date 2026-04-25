from __future__ import annotations

import requests

from app.core.config import settings


class StorageService:
    def upload_bytes(self, file_key: str, content_type: str, payload: bytes) -> None:
        if not settings.supabase_url or not settings.supabase_secret_key:
            raise RuntimeError("Supabase credentials are not configured.")

        upload_url = (
            f"{settings.supabase_url}/storage/v1/object/"
            f"{settings.supabase_bucket_name}/{file_key}"
        )

        headers = {
            "Authorization": f"Bearer {settings.supabase_secret_key}",
            "apikey": settings.supabase_secret_key,
            "Content-Type": content_type,
            "x-upsert": "true",
        }

        response = requests.post(upload_url, data=payload, headers=headers, timeout=30)
        if response.status_code >= 400:
            raise RuntimeError(f"Supabase upload failed: {response.status_code} {response.text}")

    def download_bytes(self, file_key: str) -> bytes:
        if not settings.supabase_url or not settings.supabase_secret_key:
            raise RuntimeError("Supabase credentials are not configured.")

        download_url = (
            f"{settings.supabase_url}/storage/v1/object/"
            f"{settings.supabase_bucket_name}/{file_key}"
        )
        headers = {
            "Authorization": f"Bearer {settings.supabase_secret_key}",
            "apikey": settings.supabase_secret_key,
        }
        response = requests.get(download_url, headers=headers, timeout=30)
        if response.status_code >= 400:
            raise RuntimeError(f"Supabase download failed: {response.status_code} {response.text}")
        return response.content


storage_service = StorageService()
