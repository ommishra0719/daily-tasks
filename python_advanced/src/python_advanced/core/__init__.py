"""Core utilities: exceptions, settings, and logging."""

from .exceptions import (
    AppError,
    ConfigurationError,
    DatabaseConnectionError,
    FetchTimeoutError,
    HTTPRequestError,
    JSONDecodeError,
    ValidationError,
)
from .logging_config import setup_logger
from .settings import settings

__all__ = [
    "AppError",
    "ConfigurationError",
    "DatabaseConnectionError",
    "FetchTimeoutError",
    "HTTPRequestError",
    "JSONDecodeError",
    "ValidationError",
    "settings",
    "setup_logger",
]
