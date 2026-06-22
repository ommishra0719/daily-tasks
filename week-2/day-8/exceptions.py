class AppError(Exception):
    """Base application exception."""
    pass


class FetchTimeoutError(AppError):
    """Request timed out."""
    pass


class HTTPRequestError(AppError):
    """HTTP request failed."""
    pass


class JSONDecodeError(AppError):
    """Response JSON parsing failed."""
    pass


class ConfigurationError(AppError):
    """Invalid configuration."""
    pass