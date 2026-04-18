"""
Application configuration via pydantic-settings.

All secrets are loaded from environment variables (or .env in development).
Never hardcode keys here.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Gemini ──────────────────────────────────────────────
    gemini_api_key: str = ""           # Optional when using Vertex AI on GCP

    # ── Supabase ─────────────────────────────────────────────
    supabase_url: str = ""
    supabase_anon_key: str = ""        # used for INSERT (chat, snapshots)
    supabase_service_role_key: str = ""  # used for SELECT (chat history)
    supabase_key: str = ""             # Map for Cloud Run injection helper
    supabase_jwt_secret: str = ""      # JWT secret for token verification

    # ── Google Maps ──────────────────────────────────────────
    google_maps_api_key: str = ""      # Maps JavaScript API key

    # ── App ──────────────────────────────────────────────────
    environment: str = "development"
    cache_ttl_seconds: int = 30
    rate_limit_per_minute: int = 10
    webhook_url: str = ""              # URL for mission-critical alerts

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
