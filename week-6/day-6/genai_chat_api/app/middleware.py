import logging
import time
import uuid

from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.security import peek_username_unverified

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("app.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Assigns a request ID, times every request, and logs method/path/status/
    duration/client IP. The request ID is echoed back in the X-Request-ID
    response header so client-side and server-side logs can be correlated.
    """

    async def dispatch(self, request, call_next):
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


def rate_limit_key(request) -> str:
    """
    slowapi key function: buckets logged-in users by their user ID (from the
    JWT), not by IP. This matters because several users can legitimately
    share one IP (an office NAT, a university network, a corporate VPN) --
    bucketing by IP alone would let one heavy user throttle everyone else
    behind the same address, or let many users behind that address collude
    to exceed what a single-user quota intends.

    Falls back to IP address for unauthenticated requests (e.g. hitting
    /auth/login before a token exists).
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        username = peek_username_unverified(token)
        if username:
            return f"user:{username}"
    return f"ip:{get_remote_address(request)}"
