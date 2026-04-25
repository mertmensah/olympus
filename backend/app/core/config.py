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
    reconstruct_adapter: str = os.getenv("OLYMPUS_RECONSTRUCT_ADAPTER", "mock_v1")
    hf_api_url: str = os.getenv("OLYMPUS_HF_API_URL", "")
    hf_api_token: str = os.getenv("OLYMPUS_HF_API_TOKEN", "")
    hf_api_timeout: int = int(os.getenv("OLYMPUS_HF_API_TIMEOUT", "30"))
    model_selection_strategy: str = os.getenv("OLYMPUS_MODEL_SELECTION_STRATEGY", "fixed")
    primary_adapter: str = os.getenv("OLYMPUS_PRIMARY_ADAPTER", "mock_v1")
    secondary_adapter: str = os.getenv("OLYMPUS_SECONDARY_ADAPTER", "mock_v1")
    quality_threshold: float = float(os.getenv("OLYMPUS_QUALITY_THRESHOLD", "0.7"))
    high_quality_adapter: str = os.getenv("OLYMPUS_HIGH_QUALITY_ADAPTER", "hf_api_v1")
    low_quality_adapter: str = os.getenv("OLYMPUS_LOW_QUALITY_ADAPTER", "mock_v1")
    ab_split: float = float(os.getenv("OLYMPUS_AB_SPLIT", "0.5"))
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_secret_key: str = os.getenv("SUPABASE_SECRET_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
    supabase_bucket_name: str = os.getenv("SUPABASE_BUCKET_NAME", "olympus_media")


settings = Settings()
