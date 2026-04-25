import os
from pathlib import Path

from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class Settings(BaseModel):
    app_name: str = "Olympus API"
    app_version: str = "0.1.0"
    api_public_base_url: str = os.getenv("OLYMPUS_API_BASE_URL", "http://localhost:8000")
    upload_token_secret: str = os.getenv("OLYMPUS_UPLOAD_TOKEN_SECRET", "dev-secret-change-me")
    upload_token_ttl_seconds: int = int(os.getenv("OLYMPUS_UPLOAD_TOKEN_TTL", "3600"))
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    supabase_bucket_name: str = os.getenv("SUPABASE_BUCKET_NAME", "olympus_media")


settings = Settings()
