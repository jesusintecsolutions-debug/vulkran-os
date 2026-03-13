"""VULKRAN OS — Application configuration via environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "VULKRAN OS"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://vulkran:pass@db:5432/vulkran"

    # Redis
    redis_url: str = "redis://redis:6379"

    # Auth
    secret_key: str = "CHANGE_ME"
    access_token_expire_minutes: int = 60 * 24  # 24h
    refresh_token_expire_days: int = 30
    algorithm: str = "HS256"

    # Claude API
    anthropic_api_key: str = ""
    default_model: str = "claude-sonnet-4-20250514"
    fast_model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 4096

    # Gemini
    gemini_api_key: str = ""

    # Email
    resend_api_key: str = ""
    email_from: str = "noreply@vulkran.es"

    # Storage
    data_dir: str = "/app/data"

    # CORS
    cors_origins: list[str] = ["*"]

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
