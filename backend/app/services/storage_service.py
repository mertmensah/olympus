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

    def delete_bytes(self, file_key: str) -> None:
        """Delete a file from storage. Non-fatal: logs on failure rather than raising."""
        if not settings.supabase_url or not settings.supabase_secret_key:
            return
        url = f"{settings.supabase_url}/storage/v1/object/{settings.supabase_bucket_name}/{file_key}"
        headers = {
            "Authorization": f"Bearer {settings.supabase_secret_key}",
            "apikey": settings.supabase_secret_key,
        }
        requests.delete(url, headers=headers, timeout=15)  # best-effort

    def copy_bytes(self, src_key: str, dst_key: str) -> None:
        """Server-side copy within the same bucket via Supabase copy endpoint."""
        if not settings.supabase_url or not settings.supabase_secret_key:
            raise RuntimeError("Supabase credentials are not configured.")
        url = f"{settings.supabase_url}/storage/v1/object/copy"
        headers = {
            "Authorization": f"Bearer {settings.supabase_secret_key}",
            "apikey": settings.supabase_secret_key,
            "Content-Type": "application/json",
        }
        body = {"bucketId": settings.supabase_bucket_name, "sourceKey": src_key, "destinationKey": dst_key}
        response = requests.post(url, json=body, headers=headers, timeout=30)
        if response.status_code >= 400:
            raise RuntimeError(f"Supabase copy failed: {response.status_code} {response.text}")


storage_service = StorageService()
