# FastAPI Capstone — Production-Ready Service

A small Documents API used as a vehicle to demonstrate production-readiness
practices: health vs readiness separation, a multi-stage non-root Dockerfile,
env-driven Pydantic Settings, graceful shutdown, and a
`routers / schemas / services / db` project layout.

## Project layout

```
fastapi_project/
├── app/
│   ├── main.py                 # FastAPI app: lifespan, middleware, routers
│   ├── config.py               # Pydantic Settings (env-driven config)
│   ├── middleware.py            # request logging + max-body-size middleware
│   ├── db/
│   │   ├── database.py          # async engine/session + readiness DB check
│   │   └── models.py            # SQLAlchemy ORM models
│   ├── schemas/
│   │   ├── document.py          # Pydantic request/response models
│   │   └── health.py
│   ├── services/
│   │   └── document_service.py  # business logic, DB-agnostic of HTTP layer
│   └── routers/
│       ├── documents.py         # /documents CRUD (rate-limited)
│       └── health.py            # /health and /ready
├── tests/
│   ├── conftest.py               # lifespan-aware async test client fixture
│   └── test_app.py
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile                    # multi-stage, non-root, HEALTHCHECK
├── .dockerignore
├── .env.example
└── pytest.ini
```

## Why `/health` and `/ready` are two separate endpoints

- **`/health`** — "is the process alive?" No dependency calls. Used by
  process-level monitors (Docker `HEALTHCHECK`, Kubernetes `livenessProbe`)
  to decide whether to **restart** the container. Always fast, always cheap.
- **`/ready`** — "can this instance serve traffic right now?" Actually
  round-trips to the database (`SELECT 1`) — and would check a vector store
  or LLM client too, in a fuller system. Used by load balancers / Kubernetes
  `readinessProbe` to decide whether to **route traffic**, returning `503`
  when a dependency is down. A dependency outage should stop traffic, not
  trigger a restart loop that won't fix the underlying outage.

## Running locally (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env
uvicorn app.main:app --reload
```

Then:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## Building and running with Docker

```bash
docker build -t fastapi-capstone .
docker run -p 8000:8000 --env-file .env.example fastapi-capstone
```

Then, from another terminal:
```bash
curl -i http://localhost:8000/health
curl -i http://localhost:8000/ready
```

Stop it with `docker stop <container_id>` (not `kill -9`) to see graceful
shutdown in action — uvicorn will stop accepting new connections, let
in-flight requests finish (up to the 30s `--timeout-graceful-shutdown`), the
`lifespan` shutdown block will dispose the DB engine cleanly, and only then
does the process exit.

## Key production-readiness decisions and why

| Decision | Reason |
|---|---|
| `--workers 1` in the Docker `CMD` | The app keeps in-process async state (SQLAlchemy connection pool, slowapi's in-memory rate limiter). Multiple workers would each have their own state, silently breaking rate limiting. Scale horizontally (more containers) instead, or move to `gunicorn -w N -k uvicorn.workers.UvicornWorker` with an external Redis-backed session/rate-limit store if multi-process concurrency on one host is required. |
| Multi-stage Dockerfile | Stage 1 compiles/installs into a venv with build tools present; stage 2 copies only the finished venv + app code into a slim runtime image, keeping the final image small and free of compilers. |
| Non-root `USER appuser` | Limits blast radius if the app process is ever compromised. |
| `MaxBodySizeMiddleware` | Rejects oversized requests based on `Content-Length` before the body is read into memory. This is a first line of defence only — a reverse proxy in front of this service (nginx, ALB) should enforce the same cap against chunked/lying clients. |
| `HEALTHCHECK` in the Dockerfile | Lets plain `docker ps` / any orchestrator without its own probing still see container health. |
| Pydantic `Settings` with `lru_cache` | Single source of truth for all env-driven config; parsed once per process; easy to override in tests via dependency injection. |
| `lifespan` context manager | Table creation on startup; DB engine disposal on shutdown — runs automatically around SIGTERM handling, so cleanup always happens even under container orchestration. |

## Extending readiness checks

`app/db/database.py::check_db_connection()` is the pattern to copy for any
new hard dependency (vector store, LLM API, cache, queue): write an
async function that actually calls the dependency and returns `True`/`False`,
never raises, and wire it into `DependencyStatus` and the `/ready` router.
