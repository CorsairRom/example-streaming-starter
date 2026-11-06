from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from environment variables and the local `.env` file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Example Streaming Starter"
    app_version: str = "v0.1.0"
    env: str = "local"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000

    database_url: str = "sqlite+pysqlite:///./data/app.db"

    admin_username: str = "admin"
    admin_password: str = "change-me-please"  # noqa: S105 - placeholder, overridden by .env
    session_secret: str = "change-me-too-this-signs-the-admin-cookie"  # noqa: S105
    session_https_only: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
