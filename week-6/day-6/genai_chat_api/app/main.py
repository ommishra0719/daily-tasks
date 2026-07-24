"""
App entrypoint.

Run locally with:
    uvicorn app.main:app --reload

Run in production with:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 \
        --timeout-graceful-shutdown 30
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.db.database import dispose_engine, init_models
from app.middleware import RequestLoggingMiddleware
from app.rate_limit import limiter
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.health import router as health_router

logger = logging.getLogger("app.lifespan")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("Starting up: creating database tables if needed...")
    await init_models()
    logger.info("Startup complete.")

    yield

    # --- Shutdown ---
    logger.info("Shutting down: closing database connections...")
    await dispose_engine()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# --- Middleware ---
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Rate limiting (per-user, see app/middleware.py:rate_limit_key) ---
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please slow down and try again shortly."},
    )


# --- Routers ---
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(chat_router)


@app.get("/")
async def root():
    return {"message": f"{settings.APP_NAME} v{settings.APP_VERSION}"}
