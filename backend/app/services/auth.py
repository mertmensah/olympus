from __future__ import annotations

import requests
from fastapi import Header, HTTPException

from app.core.config import settings
from app.models.schemas import AuthUser
from app.services.database import database


def _verify_supabase_access_token(access_token: str) -> AuthUser:
    if not settings.supabase_url:
        raise HTTPException(status_code=500, detail="SUPABASE_URL not configured")

    auth_url = f"{settings.supabase_url}/auth/v1/user"
    api_key = settings.supabase_anon_key or settings.supabase_secret_key
    if not api_key:
        raise HTTPException(status_code=500, detail="Supabase API key not configured (SUPABASE_ANON_KEY or SUPABASE_SECRET_KEY)")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "apikey": api_key,
    }

    try:
        response = requests.get(auth_url, headers=headers, timeout=8)
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail=f"Auth verification failed: {exc}") from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid or expired access token (Supabase status: {response.status_code})",
        )

    payload = response.json()
    user_id = payload.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token verification returned no user id")

    email = payload.get("email")
    database.upsert_user_profile(str(user_id), email)
    return AuthUser(id=str(user_id), email=email)


def get_current_user(authorization: str | None = Header(default=None)) -> AuthUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    return _verify_supabase_access_token(token)
