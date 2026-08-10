from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "RAG Assistant"
    APP_VERSION: str = "1.0.0"

    # Security
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./rag_assistant.db"

    # Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash-lite"
    GEMINI_CALL_DELAY: float = 5.0   # seconds between calls (free tier: 15 RPM)

    # RAG
    RETRIEVAL_K: int = 5
    CACHE_TTL_SECONDS: int = 300
    CACHE_MAX_SIZE: int = 256
    CHUNK_SIZE: int = 400
    CHUNK_OVERLAP: int = 80

    # Eval baselines (block deployment if any metric drops below baseline - 0.1)
    EVAL_BASELINE_FAITHFULNESS: float = 0.80
    EVAL_BASELINE_RELEVANCY: float = 0.30

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
