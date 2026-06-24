"""Pytest configuration and fixtures."""

import pytest


# Register markers
def pytest_configure(config):  # type: ignore
    """Register pytest markers."""
    config.addinivalue_line("markers", "asyncio: mark test as async")
    config.addinivalue_line("markers", "slow: mark test as slow")
    config.addinivalue_line("markers", "integration: mark test as integration")


@pytest.fixture
def sample_text() -> str:
    """Provide sample text for tests."""
    return "This is a sample text. It has multiple sentences. And different words."


@pytest.fixture
def sample_texts() -> list[str]:
    """Provide sample texts list for tests."""
    return [
        "First text with some content",
        "Second text with different words",
        "Third text with repeated content",
    ]
