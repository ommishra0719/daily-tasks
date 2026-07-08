# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1: builder
# Installs dependencies into an isolated virtualenv. Nothing from this stage
# except the finished venv is copied into the final image, so build tools,
# pip caches, and wheel files never bloat the runtime image.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Build-time only OS packages needed to compile any C-extension wheels
# (e.g. for cryptography/aiosqlite deps). Removed entirely in the final
# stage since this whole layer is discarded.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


# ---------------------------------------------------------------------------
# Stage 2: runtime
# Slim final image: just the venv + app code + a non-root user. No compilers,
# no pip cache, no build-essential.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Create a dedicated, unprivileged user/group to run the app as.
# Running as root inside a container is a needless privilege-escalation
# risk if the app is ever compromised.
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Bring in the pre-built virtualenv from the builder stage only.
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# App code, owned by appuser from the start (avoids an extra chown layer).
COPY --chown=appuser:appuser ./app ./app

USER appuser

EXPOSE 8000

# Container-level liveness check mirrors the /health endpoint so `docker ps`
# and orchestrators without their own probing (e.g. plain Docker, ECS) can
# still detect a stuck process.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else sys.exit(1)"

# --workers 1 because this app keeps async, in-process state (the slowapi
# limiter and the SQLAlchemy async engine's connection pool) that is not
# shared across processes. Scale horizontally (more containers behind a load
# balancer) or move to gunicorn -w N -k uvicorn.workers.UvicornWorker with an
# external session/rate-limit store (e.g. Redis) if multi-process concurrency
# is needed on a single host.
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--timeout-graceful-shutdown", "30"]
