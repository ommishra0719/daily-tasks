"""Tests for core module."""

import pytest

from python_advanced.core import (
    AppError,
    ConfigurationError,
    DatabaseConnectionError,
    FetchTimeoutError,
    HTTPRequestError,
    JSONDecodeError,
    ValidationError,
)


class TestExceptions:
    """Test custom exceptions."""

    def test_app_error(self) -> None:
        """Test base AppError."""
        with pytest.raises(AppError):
            raise AppError("Test error")

    def test_fetch_timeout_error(self) -> None:
        """Test FetchTimeoutError."""
        with pytest.raises(FetchTimeoutError):
            raise FetchTimeoutError("Timeout occurred")

    def test_http_request_error(self) -> None:
        """Test HTTPRequestError."""
        with pytest.raises(HTTPRequestError):
            raise HTTPRequestError("Request failed")

    def test_exception_inheritance(self) -> None:
        """Test that custom exceptions inherit from AppError."""
        errors = [
            FetchTimeoutError("test"),
            HTTPRequestError("test"),
            JSONDecodeError("test"),
            ConfigurationError("test"),
            DatabaseConnectionError("test"),
            ValidationError("test"),
        ]

        for error in errors:
            assert isinstance(error, AppError)


class TestSettings:
    """Test settings configuration."""

    def test_settings_defaults(self) -> None:
        """Test default settings values."""
        from python_advanced.core import settings

        assert settings.log_level == "INFO"
        assert settings.timeout == 5.0
        assert settings.max_retries == 3
        assert settings.retry_delay == 0.1

    def test_settings_are_accessible(self) -> None:
        """Test that settings can be accessed."""
        from python_advanced.core import settings

        # Should not raise
        log_level = settings.log_level
        timeout = settings.timeout
        assert log_level is not None
        assert timeout is not None


class TestLogger:
    """Test logging configuration."""

    def test_logger_setup(self) -> None:
        """Test that logger can be set up."""
        from python_advanced.core import setup_logger

        logger = setup_logger()
        assert logger is not None

    def test_logger_can_log(self) -> None:
        """Test that logger can log messages."""
        from python_advanced.core import setup_logger

        logger = setup_logger()

        # Should not raise
        logger.info("Test message")
        logger.debug("Debug message")
        logger.warning("Warning message")
