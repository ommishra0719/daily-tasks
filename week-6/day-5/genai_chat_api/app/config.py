"""
Centralised application configuration.

Everything that varies between environments (local, staging, prod, tests)
lives here and is read from environment variables / a `.env` file. Nothing
else in the app should call `os.environ` directly -- always import
`settings` from this module so there is exactly one source of truth.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # --- General ---
    APP_NAME: str = "GenAI Authenticated Chat API"
    APP_VERSION: str = "1.0.0"
    ENV: str = Field(default="development")  # development | staging | production
    DEBUG: bool = False

    # --- Security / JWT ---
    # Never commit a real secret; this default only exists so local dev
    # doesn't crash if the .env file is missing. Production MUST override it.
    SECRET_KEY: str = "change-me-in-env"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:3000"

    # --- Database ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./genai_chat.db"

    # --- Gemini ---
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # --- System prompt registry ---
    PROMPTS_FILE: str = str(BASE_DIR / "app" / "prompts.yaml")

    # --- Conversation window management ---
    # How many of the most recent messages (user + model turns combined) are
    # sent to the model as context. Older turns stay in the DB (the history
    # endpoint always returns everything) but are dropped from the prompt
    # sent to Gemini once the window fills up.
    MAX_CONTEXT_MESSAGES: int = 10
    # Soft token ceiling for the assembled context; if exceeded we trim the
    # oldest messages further, even if MAX_CONTEXT_MESSAGES hasn't been hit.
    MAX_CONTEXT_TOKENS: int = 6000

    # --- Rate limiting ---
    RATE_LIMIT_MESSAGE: str = "20/minute"
    RATE_LIMIT_AUTH: str = "10/minute"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor -- the .env / environment is parsed once."""
    return Settings()


settings = get_settings()
