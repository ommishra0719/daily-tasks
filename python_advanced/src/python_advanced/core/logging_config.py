"""Structured logging configuration using loguru."""

import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from .settings import settings


def _json_sink(message: str) -> None:
    """
    Write log record as JSON to file.

    Args:
        message: Formatted log message
    """
    # message here is already the formatted output
    # We'll parse it and re-structure it
    pass


def setup_logger() -> Any:
    """
    Configure loguru with structured logging.

    Returns:
        Loguru logger instance configured with:
        - Stderr output (colorized)
        - JSON file output with rotation and compression
        - Structured logging with correlation IDs

    Example:
        >>> logger = setup_logger()
        >>> logger.bind(request_id="abc-123").info("Processing request")
    """
    # Remove default handler
    logger.remove()

    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Add stderr handler (colored, for development)
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>",
        level=settings.log_level,
        colorize=True,
    )

    # Add JSON file handler (structured, for production/analysis)
    def json_formatter(record: dict[str, Any]) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "logger": record["name"],
            "function": record["function"],
            "line": record["line"],
            "message": record["message"],
        }

        # Include extra fields (like request_id) from context
        if record["extra"]:
            log_data.update(record["extra"])

        return json.dumps(log_data) + "\n"

    logger.add(
        str(logs_dir / "app.json"),
        format=json_formatter,  # type: ignore
        level=settings.log_level,
        rotation="10 MB",
        compression="zip",
        serialize=False,
    )

    return logger
