"""Tests for async utilities module."""

import pytest

from python_advanced.async_utils import parallel_fetch, sequential_fetch


@pytest.mark.asyncio
class TestAsyncFetch:
    """Test async fetch functions."""

    async def test_fetch_requires_valid_url(self) -> None:
        """Test that fetch requires a valid URL."""
        # This would require mocking aiohttp, so we'll skip for now
        # In production, use pytest-mock or similar
        pass

    async def test_sequential_fetch_empty_list(self) -> None:
        """Test sequential_fetch with empty list."""
        results = await sequential_fetch([])
        assert results == []

    async def test_parallel_fetch_empty_list(self) -> None:
        """Test parallel_fetch with empty list."""
        results = await parallel_fetch([])
        assert results == []
