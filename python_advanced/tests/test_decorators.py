"""Tests for decorators module."""

import time

import pytest

from python_advanced.core import AppError
from python_advanced.decorators import UnstableAPI, retry, timeit


class TestTimeitDecorator:
    """Test timeit decorator."""

    def test_timeit_measures_time(self) -> None:
        """Test that timeit measures execution time."""

        @timeit
        def slow_function() -> str:
            time.sleep(0.1)
            return "done"

        result = slow_function()
        assert result == "done"

    def test_timeit_preserves_metadata(self) -> None:
        """Test that timeit preserves function metadata."""

        @timeit
        def my_function() -> str:
            """My docstring."""
            return "result"

        assert my_function.__name__ == "my_function"
        assert "docstring" in my_function.__doc__


class TestRetryDecorator:
    """Test retry decorator."""

    def test_retry_success_on_first_attempt(self) -> None:
        """Test retry when function succeeds immediately."""

        call_count = 0

        @retry(max_attempts=3, delay=0.01)
        def successful_function() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()
        assert result == "success"
        assert call_count == 1

    def test_retry_success_after_failures(self) -> None:
        """Test retry succeeds after some failures."""

        call_count = 0

        @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        def eventually_succeeds() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"

        result = eventually_succeeds()
        assert result == "success"
        assert call_count == 3

    def test_retry_max_attempts_exceeded(self) -> None:
        """Test retry fails after max attempts."""

        @retry(max_attempts=2, delay=0.01, exceptions=(ValueError,))
        def always_fails() -> None:
            raise ValueError("Always fails")

        with pytest.raises(AppError):
            always_fails()

    def test_retry_wrong_exception_not_retried(self) -> None:
        """Test retry doesn't retry wrong exception type."""

        @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        def raises_type_error() -> None:
            raise TypeError("Wrong type")

        with pytest.raises(TypeError):
            raises_type_error()


class TestUnstableAPI:
    """Test UnstableAPI class."""

    def test_unstable_api_initialization(self) -> None:
        """Test UnstableAPI initialization."""
        api = UnstableAPI(failure_rate=0.0)  # No failures
        assert api.failure_rate == 0.0
        assert api.attempt_count == 0

    def test_unstable_api_no_failures(self) -> None:
        """Test UnstableAPI with no failures."""
        api = UnstableAPI(failure_rate=0.0)
        result = api.fetch_data("/users")
        assert result["endpoint"] == "/users"
        assert result["data"] == "success"

    def test_unstable_api_retries_on_failures(self) -> None:
        """Test UnstableAPI retries after failures."""
        api = UnstableAPI(failure_rate=0.5)
        # With retry decorator, this should eventually succeed
        result = api.fetch_data("/data")
        assert result["data"] == "success"
