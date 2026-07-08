"""
Centralised application configuration.

Everything that varies between environments (local, staging, prod) lives
here and is read from environment variables / a .env file. Nothing in the
rest of the app should call os.environ directly — always import `settings`
from this module so there is exactly one source of truth for config.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- General ---
    APP_NAME: str = "FastAPI Capstone Service"
    APP_VERSION: str = "1.0.0"
    ENV: str = Field(default="development")  # development | staging | production
    DEBUG: bool = False

    # --- Security ---
    # Never commit a real secret; this default only exists so local dev
    # doesn't crash if the .env file is missing. Production MUST override it.
    SECRET_KEY: str = "change-me-in-env"

    # --- CORS ---
    # Comma-separated list of allowed origins, e.g.
    # "https://app.example.com,https://admin.example.com"
    CORS_ORIGINS: str = "http://localhost:3000"

    # --- Database ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"

    # --- Rate limiting ---
    RATE_LIMIT_DEFAULT: str = "60/minute"

    # --- Request limits ---
    MAX_UPLOAD_SIZE_BYTES: int = 100 * 1024 * 1024  # 100 MB

    # --- Graceful shutdown ---
    # Mirrors --timeout-graceful-shutdown passed to uvicorn/gunicorn so the
    # app-level shutdown logic and the server-level timeout stay in sync.
    GRACEFUL_SHUTDOWN_TIMEOUT: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings accessor. lru_cache means the .env file / environment is
    only parsed once per process, and the same Settings instance is reused
    everywhere (import get_settings and call it, rather than constructing
    Settings() directly, so tests can override it via dependency overrides).
    """
    return Settings()


settings = get_settings()
