"""Unstable API example for demonstrating retry decorator."""

import random
from typing import Any

from .utils import retry


class UnstableAPI:
    """Simulated unstable API with retry capability."""

    def __init__(self, failure_rate: float = 0.7):
        """
        Initialize unstable API.

        Args:
            failure_rate: Probability of failure (0.0-1.0)
        """
        self.failure_rate = failure_rate
        self.attempt_count = 0

    @retry(max_attempts=5, delay=0.1, exceptions=(RuntimeError,))
    def fetch_data(self, endpoint: str) -> dict[str, Any]:
        """
        Simulate API fetch with random failures.

        Args:
            endpoint: API endpoint

        Returns:
            Dictionary with data

        Raises:
            RuntimeError: Randomly raised to simulate API failures
        """
        self.attempt_count += 1

        if random.random() < self.failure_rate:
            msg = f"API request to {endpoint} failed (attempt {self.attempt_count})"
            raise RuntimeError(msg)

        return {"endpoint": endpoint, "data": "success", "attempt": self.attempt_count}
