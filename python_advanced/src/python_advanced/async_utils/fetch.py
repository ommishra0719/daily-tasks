"""Async utilities for HTTP operations with structured logging."""

import asyncio
import uuid
from typing import Any

import aiohttp
from loguru import logger

from ..core import FetchTimeoutError, HTTPRequestError, settings


async def fetch(
    url: str,
    method: str = "GET",
    request_id: str | None = None,
    timeout: float | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Fetch data from a URL asynchronously with correlation ID.

    Args:
        url: URL to fetch
        method: HTTP method (GET, POST, etc.)
        request_id: Correlation ID for request tracking (generated if not provided)
        timeout: Request timeout in seconds (uses settings.timeout if not provided)
        **kwargs: Additional kwargs for aiohttp ClientSession.request()

    Returns:
        Dictionary with response data and metadata

    Raises:
        FetchTimeoutError: If request times out
        HTTPRequestError: If request fails

    Example:
        >>> result = await fetch(
        ...     "https://api.example.com/data",
        ...     request_id="abc-123"
        ... )
    """
    request_id = request_id or str(uuid.uuid4())
    timeout_val = timeout or settings.timeout

    logger_bound = logger.bind(request_id=request_id)

    try:
        async with aiohttp.ClientSession() as session:
            logger_bound.debug(f"Fetching {method} {url}")

            try:
                async with session.request(method, url, timeout=aiohttp.ClientTimeout(total=timeout_val), **kwargs) as response:
                    data = await response.json()
                    logger_bound.info(f"Successfully fetched {url} (status: {response.status})")
                    return {
                        "url": url,
                        "status": response.status,
                        "data": data,
                        "request_id": request_id,
                    }
            except asyncio.TimeoutError as e:
                msg = f"Request to {url} timed out after {timeout_val}s"
                logger_bound.error(msg)
                raise FetchTimeoutError(msg) from e

    except aiohttp.ClientError as e:
        msg = f"HTTP request to {url} failed: {e}"
        logger_bound.error(msg)
        raise HTTPRequestError(msg) from e


async def sequential_fetch(urls: list[str], request_id: str | None = None) -> list[dict[str, Any]]:
    """
    Fetch multiple URLs sequentially.

    Args:
        urls: List of URLs to fetch
        request_id: Shared correlation ID for all requests

    Returns:
        List of response dictionaries

    Example:
        >>> urls = ["https://api.example.com/1", "https://api.example.com/2"]
        >>> results = await sequential_fetch(urls)
    """
    request_id = request_id or str(uuid.uuid4())
    logger.bind(request_id=request_id).info(f"Fetching {len(urls)} URLs sequentially")

    results: list[dict[str, Any]] = []
    for url in urls:
        try:
            result = await fetch(url, request_id=request_id)
            results.append(result)
        except (FetchTimeoutError, HTTPRequestError) as e:
            logger.bind(request_id=request_id).warning(f"Skipping {url}: {e}")
            results.append({"url": url, "error": str(e), "request_id": request_id})

    return results


async def parallel_fetch(
    urls: list[str], request_id: str | None = None
) -> list[dict[str, Any]]:
    """
    Fetch multiple URLs in parallel using asyncio.gather.

    Args:
        urls: List of URLs to fetch
        request_id: Shared correlation ID for all requests

    Returns:
        List of response dictionaries

    Example:
        >>> urls = ["https://api.example.com/1", "https://api.example.com/2"]
        >>> results = await parallel_fetch(urls)
    """
    request_id = request_id or str(uuid.uuid4())
    logger.bind(request_id=request_id).info(f"Fetching {len(urls)} URLs in parallel")

    tasks = [fetch(url, request_id=request_id) for url in urls]

    results_raw: list[Any] = await asyncio.gather(*tasks, return_exceptions=True)

    processed_results: list[dict[str, Any]] = []
    for result in results_raw:
        if isinstance(result, Exception):
            processed_results.append({"error": str(result), "request_id": request_id})
        else:
            processed_results.append(result)

    return processed_results
