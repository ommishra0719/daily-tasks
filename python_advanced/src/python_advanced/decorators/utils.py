"""Decorators for timing, retrying, and other utilities."""

import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar, cast

from loguru import logger

from ..core import AppError

F = TypeVar("F", bound=Callable[..., Any])


def timeit(func: F) -> F:
    """
    Decorator to measure function execution time.

    Args:
        func: Function to time

    Returns:
        Wrapper function that logs execution time

    Example:
        >>> @timeit
        ... def slow_function():
        ...     time.sleep(1)
        >>> slow_function()  # Logs execution time
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info(f"{func.__name__} took {elapsed:.4f} seconds")
        return result

    return cast(F, wrapper)


def retry(
    max_attempts: int = 3, delay: float = 0.1, exceptions: tuple[type[Exception], ...] = (Exception,)
) -> Callable[[F], F]:
    """
    Decorator factory for retrying failed function calls.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Delay in seconds between retries
        exceptions: Tuple of exception types to catch and retry on

    Returns:
        Decorator function

    Example:
        >>> @retry(max_attempts=3, delay=0.5, exceptions=(ValueError,))
        ... def unstable_function():
        ...     if random.random() < 0.5:
        ...         raise ValueError("Random failure")
        ...     return "success"
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    logger.debug(f"Attempt {attempt}/{max_attempts} for {func.__name__}")
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(
                        f"Attempt {attempt} failed: {e}. "
                        f"Retrying in {delay}s..." if attempt < max_attempts else ""
                    )
                    if attempt < max_attempts:
                        time.sleep(delay)

            error_msg = f"Failed after {max_attempts} attempts"
            logger.error(error_msg, exc_info=last_exception)
            raise AppError(error_msg) from last_exception

        return cast(F, wrapper)

    return decorator
