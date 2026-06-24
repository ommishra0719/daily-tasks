"""Configuration management using Pydantic."""

import os
from typing import Literal

from pydantic import BaseModel


class Settings(BaseModel):
    """Application settings with environment variable support."""

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    timeout: float = 5.0
    max_retries: int = 3
    retry_delay: float = 0.1

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        return cls(
            log_level=os.getenv("APP_LOG_LEVEL", "INFO"),  # type: ignore
            timeout=float(os.getenv("APP_TIMEOUT", "5.0")),
            max_retries=int(os.getenv("APP_MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("APP_RETRY_DELAY", "0.1")),
        )


# Global settings instance
settings: Settings = Settings.from_env()
