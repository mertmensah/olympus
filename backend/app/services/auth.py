from __future__ import annotations

import requests
from fastapi import Header, HTTPException

from app.core.config import settings
from app.models.schemas import AuthUser


def _verify_supabase_access_token(access_token: str) -> AuthUser:
    if not settings.supabase_url:
        raise HTTPException(status_code=500, detail="SUPABASE_URL not configured")

    auth_url = f"{settings.supabase_url}/auth/v1/user"
    api_key = settings.supabase_secret_key or settings.supabase_anon_key
    if not api_key:
        raise HTTPException(status_code=500, detail="Supabase API key not configured")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "apikey": api_key,
    }

    try:
        response = requests.get(auth_url, headers=headers, timeout=8)
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail=f"Auth verification failed: {exc}") from exc

    if response.status_code >= 400:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")

    payload = response.json()
    return AuthUser(id=str(payload.get("id")), email=payload.get("email"))


def get_current_user(authorization: str | None = Header(default=None)) -> AuthUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    return _verify_supabase_access_token(token)
