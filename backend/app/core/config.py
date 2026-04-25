import os

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Olympus API"
    app_version: str = "0.1.0"
    api_public_base_url: str = os.getenv("OLYMPUS_API_BASE_URL", "http://localhost:8000")
    upload_token_secret: str = os.getenv("OLYMPUS_UPLOAD_TOKEN_SECRET", "dev-secret-change-me")
    upload_token_ttl_seconds: int = int(os.getenv("OLYMPUS_UPLOAD_TOKEN_TTL", "3600"))


settings = Settings()
