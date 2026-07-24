"""
Single shared `Limiter` instance, keyed per-user (see `rate_limit_key`).
Both `app.main` (registers it on app.state + the exception handler) and the
routers (apply `@limiter.limit(...)` to individual endpoints) import this
same object, so there's exactly one limiter and one set of buckets.
"""

from slowapi import Limiter

from app.middleware import rate_limit_key

limiter = Limiter(key_func=rate_limit_key)
