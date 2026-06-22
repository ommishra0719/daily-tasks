import asyncio
import aiohttp
import time
import uuid

# ===== NEW (Day-8): Needed for importing files from week-2/day-8 =====
import sys
from pathlib import Path

# Go up to project root
project_root = Path(__file__).resolve().parents[2]

# Add week-2/day-8 to sys.path
sys.path.append(
    str(project_root / "week-2" / "day-8")
)

# ===== NEW (Day-8): Import logger configuration and exceptions =====
from logging_config import setup_logger
from exceptions import (
    FetchTimeoutError,
    HTTPRequestError
)

# ===== NEW (Day-8): Initialize Loguru logger =====
logger = setup_logger()

URLS = [
    "https://jsonplaceholder.typicode.com/posts/1",
    "https://jsonplaceholder.typicode.com/posts/2",
    "https://jsonplaceholder.typicode.com/posts/3",
    "https://jsonplaceholder.typicode.com/posts/4",
    "https://jsonplaceholder.typicode.com/posts/5"
]


# ===== CHANGED (Day-8): Added request_id parameter =====
async def fetch(session, url, request_id):

    # ===== NEW (Day-8): Structured logger with correlation ID =====
    log = logger.bind(request_id=request_id)

    try:

        # ===== NEW (Day-8): Measure latency =====
        start = time.perf_counter()

        async with asyncio.timeout(5):

            async with session.get(url) as response:

                response.raise_for_status()

                data = await response.json()

                # ===== NEW (Day-8): Calculate latency =====
                latency_ms = (
                    time.perf_counter() - start
                ) * 1000

                # ===== CHANGED (Day-8): Structured logging =====
                log.info(
                    f"Fetched {url} "
                    f"(latency={latency_ms:.2f} ms)"
                )

                return data

    # ===== CHANGED (Day-8): Custom exception =====
    except TimeoutError:

        log.error(f"Timeout while fetching {url}")

        raise FetchTimeoutError(
            f"Request timed out for {url}"
        )

    # ===== CHANGED (Day-8): More specific exception =====
    except aiohttp.ClientError as e:

        log.error(
            f"HTTP request failed for {url}: {e}"
        )

        raise HTTPRequestError(
            f"HTTP request failed for {url}"
        )


async def sequential_fetch():

    # ===== NEW (Day-8): Correlation ID =====
    request_id = str(uuid.uuid4())

    async with aiohttp.ClientSession() as session:

        results = []

        for url in URLS:

            # ===== CHANGED (Day-8): Pass request_id =====
            result = await fetch(
                session,
                url,
                request_id
            )

            results.append(result)

        return results


async def concurrent_fetch():

    # ===== NEW (Day-8): Correlation ID =====
    request_id = str(uuid.uuid4())

    async with aiohttp.ClientSession() as session:

        tasks = [
            # ===== CHANGED (Day-8): Pass request_id =====
            fetch(session, url, request_id)
            for url in URLS
        ]

        # ===== CHANGED (Day-8): Preserve exceptions =====
        results = await asyncio.gather(
            *tasks,
            return_exceptions=True
        )

        return results


async def main():

    start = time.perf_counter()

    sequential_results = await sequential_fetch()

    sequential_time = time.perf_counter() - start

    # ===== CHANGED (Day-8): Loguru logger instead of logging.info =====
    logger.info(
        f"Sequential completed in "
        f"{sequential_time:.4f} seconds"
    )

    start = time.perf_counter()

    concurrent_results = await concurrent_fetch()

    concurrent_time = time.perf_counter() - start

    logger.info(
        f"Concurrent completed in "
        f"{concurrent_time:.4f} seconds"
    )

    logger.info(
        f"Speedup = "
        f"{sequential_time/concurrent_time:.2f}x"
    )


if __name__ == "__main__":

    asyncio.run(main())