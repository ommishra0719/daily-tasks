"""
/health vs /ready — these answer two different questions and must never be
merged into one endpoint:

  /health  -> "Is this process alive and able to respond at all?"
              Used by process/container orchestrators (e.g. Kubernetes
              livenessProbe, Docker HEALTHCHECK) to decide whether to KILL
              and restart the container. It should be nearly free to
              compute and must not depend on external systems — if the DB
              is down but the process itself is fine, /health must still
              return 200, otherwise the orchestrator will restart a
              perfectly healthy process in a crash loop while the real
              problem (the DB) goes unaddressed.

  /ready   -> "Can this instance actually serve traffic right now?"
              Used by load balancers / Kubernetes readinessProbe to decide
              whether to ROUTE traffic here. It checks every hard
              dependency (DB, and in a fuller system: vector store, LLM
              client, cache, message queue...). If any check fails, /ready
              returns 503 so the load balancer stops sending requests to
              this pod, but the process is left running (no restart) since
              restarting won't fix an external dependency outage.
"""

from fastapi import APIRouter, Response, status

from app.config import settings
from app.db.database import check_db_connection
from app.schemas.health import DependencyStatus, HealthResponse, ReadyResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    """Cheap liveness check — no dependency calls, always fast."""
    return HealthResponse(status="ok", version=settings.APP_VERSION)


@router.get("/ready", response_model=ReadyResponse)
async def ready(response: Response):
    """Readiness check — verifies every hard dependency is reachable."""
    db_ok = await check_db_connection()

    # Extend this dict as more dependencies (vector store, LLM client,
    # cache, queue...) are added to the system.
    dependencies = DependencyStatus(database=db_ok)
    all_ok = all(dependencies.model_dump().values())

    if not all_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadyResponse(
        status="ready" if all_ok else "not_ready",
        dependencies=dependencies,
    )
