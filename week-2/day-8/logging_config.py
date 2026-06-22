import sys
from loguru import logger


def setup_logger():

    logger.remove()

    # Default values for extra fields
    logger.configure(
        extra={
            "request_id": "N/A"
        }
    )

    logger.add(
        sys.stderr,
        level="INFO",
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level}</level> | "
            "{extra[request_id]} | "
            "{message}"
        )
    )

    logger.add(
        "logs/app.json",
        serialize=True,
        rotation="10 MB",
        compression="zip"
    )

    return logger