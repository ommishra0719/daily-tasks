"""Custom exceptions for the python_advanced package."""


class AppError(Exception):
    """Base exception for all application errors."""

    pass


class FetchTimeoutError(AppError):
    """Raised when an async fetch operation times out."""

    pass


class HTTPRequestError(AppError):
    """Raised when an HTTP request fails."""

    pass


class JSONDecodeError(AppError):
    """Raised when JSON decoding fails."""

    pass


class ConfigurationError(AppError):
    """Raised when configuration is invalid."""

    pass


class DatabaseConnectionError(AppError):
    """Raised when database connection fails."""

    pass


class ValidationError(AppError):
    """Raised when validation fails."""

    pass
