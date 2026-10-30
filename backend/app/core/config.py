from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ENV, env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Orbit API"
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://orbit:orbit@localhost:5432/orbit"
    firebase_project_id: str | None = None
    firebase_service_account_file: str | None = None
    firebase_check_revoked: bool = True
    cors_origins: list[str] = ["http://localhost:3000"]
    upload_dir: str = "./var/uploads"
    max_upload_mb: int = 10
    orbit_ai_base_url: str | None = None
    orbit_ai_api_key: str | None = None
    orbit_ai_model: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
