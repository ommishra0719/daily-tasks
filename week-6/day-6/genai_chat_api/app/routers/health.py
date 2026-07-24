from fastapi import APIRouter

from app.db.database import check_db_connection

router = APIRouter(tags=["Health"])


@router.get("/health/live")
async def liveness():
    """Process is up. Doesn't touch the DB -- always cheap and fast."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness():
    """Process is up AND can actually reach the database."""
    db_ok = await check_db_connection()
    status_code = "ready" if db_ok else "not_ready"
    return {"status": status_code, "database": db_ok}
