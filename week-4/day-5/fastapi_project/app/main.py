"""
App entrypoint.

Run locally with:
    uvicorn app.main:app --reload

Run in production with (see Dockerfile CMD):
    uvicorn app.main:app --host 0.0.0.0 --port 8000 \
        --workers 1 --timeout-graceful-shutdown 30
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.db.database import dispose_engine, init_models
from app.middleware import MaxBodySizeMiddleware, RequestLoggingMiddleware
from app.routers.documents import router as documents_router
from app.routers.health import router as health_router

logger = logging.getLogger("app.lifespan")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("Starting up: creating database tables if needed...")
    await init_models()
    logger.info("Startup complete.")

    yield  # <-- app serves requests while suspended here

    # --- Shutdown ---
    # Runs when the process receives SIGTERM (e.g. `docker stop`, a
    # Kubernetes pod eviction, or a rolling deploy). Uvicorn has already
    # stopped accepting new connections and is waiting (up to
    # --timeout-graceful-shutdown seconds) for in-flight requests — such as
    # a long LLM stream — to finish before this code runs its course and
    # the process exits. Use this block to flush anything still pending and
    # release external resources cleanly.
    logger.info("Shutting down: flushing pending work and closing connections...")
    await dispose_engine()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# --- Middleware (order matters: outermost added last is outermost applied) ---
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(MaxBodySizeMiddleware, max_body_size=settings.MAX_UPLOAD_SIZE_BYTES)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Rate limiting ---
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please wait before trying again."},
    )


# --- Routers ---
app.include_router(health_router)
app.include_router(documents_router)


@app.get("/")
async def root():
    return {"message": f"{settings.APP_NAME} v{settings.APP_VERSION}"}
