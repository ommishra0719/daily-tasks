"""
Cross-cutting HTTP middleware:

1. RequestLoggingMiddleware — structured, one-line-per-request logging to
   stdout (so the container runtime / log collector can capture it), with a
   request ID that is echoed back in the response headers for tracing.

2. MaxBodySizeMiddleware — rejects requests whose declared Content-Length
   exceeds the configured limit *before* the body is read into memory, so a
   single huge upload can't exhaust server RAM.
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-ID"] = request_id

        client_ip = request.client.host if request.client else "unknown"

        logger.info(
            "[%s] %s %s | %s | %.2fms | ip=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            client_ip,
        )

        return response


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """
    Enforces a hard cap on request body size using the Content-Length
    header. This is a first line of defence — it is cheap and rejects
    obviously oversized requests immediately. It does NOT protect against a
    client that lies about Content-Length and streams a huge chunked body;
    that case should also be capped at the reverse proxy / load balancer
    level (e.g. client_max_body_size in nginx) in front of this service.
    """

    def __init__(self, app, max_body_size: int):
        super().__init__(app)
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")

        if content_length is not None:
            try:
                if int(content_length) > self.max_body_size:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": (
                                "Request body too large. "
                                f"Limit is {self.max_body_size} bytes."
                            )
                        },
                    )
            except ValueError:
                # Malformed header — let downstream handling deal with it.
                pass

        return await call_next(request)
