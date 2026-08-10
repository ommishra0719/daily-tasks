"""
RAG Assistant — Capstone entrypoint.

Composes all week-3 through week-8 patterns:
  - FastAPI app structure (week-3/week-4)
  - JWT auth (week-3/day-5, week-6/day-5)
  - Async SQLite via SQLAlchemy (week-4/day-1)
  - Gemini generation + streaming (week-5/day-5)
  - BM25 retrieval + chunking (week-7)
  - Conversational RAG (week-8/day-1)
  - Eval harness (week-8/day-2)
  - Multi-query retrieval (week-8/day-3)
  - Async ingestion + TTL cache + /stats (week-8/day-4)

Run: uvicorn app.main:app --reload
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db.database import dispose_engine, init_models
from app.db.models import User
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.documents import router as documents_router
from app.security import get_current_user
from app.services.rag import index, metrics

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("main")

# Seed the index with the support KB from week-8 so the system is immediately queryable
_SEED_KB = [
    ("Standard shipping takes 5-7 business days within the continental US.", "seed-kb"),
    ("Express shipping costs an additional $15 and delivers in 1-2 business days.", "seed-kb"),
    ("We do not currently ship internationally outside the US and Canada.", "seed-kb"),
    ("Items can be returned within 30 days of delivery for a full refund.", "seed-kb"),
    ("Return shipping labels are free for defective items, otherwise the customer pays return postage.", "seed-kb"),
    ("Refunds are issued to the original payment method within 5-10 business days of receiving the item.", "seed-kb"),
    ("All electronics come with a 1-year manufacturer warranty covering defects.", "seed-kb"),
    ("The warranty does not cover accidental damage, water damage, or unauthorized repairs.", "seed-kb"),
    ("To file a warranty claim, contact support with your order ID and description of the issue.", "seed-kb"),
    ("Passwords must be at least 10 characters and include one number and one symbol.", "seed-kb"),
    ("Two-factor authentication can be enabled from the Security tab in account settings.", "seed-kb"),
    ("Subscription plans are billed monthly and can be cancelled at any time from the billing page.", "seed-kb"),
    ("Cancelling a subscription stops future charges but does not refund the current billing period.", "seed-kb"),
    ("We accept Visa, Mastercard, American Express, and PayPal for payment.", "seed-kb"),
    ("Gift cards do not expire and can be combined with other payment methods at checkout.", "seed-kb"),
    ("Customer support is available via live chat 9am-6pm ET, Monday through Friday.", "seed-kb"),
    ("Bulk orders of 50+ units qualify for a 10% discount; contact sales for a quote.", "seed-kb"),
    ("The mobile app is available on iOS 15+ and Android 10+.", "seed-kb"),
    ("Order status can be tracked in real time from the 'My Orders' page after logging in.", "seed-kb"),
    ("You can create an account using an email address or by signing in with Google.", "seed-kb"),
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Startup: initialising DB and index...")
    await init_models()
    index.add([text for text, _ in _SEED_KB], "seed-kb")
    logger.info(f"Index seeded with {index.size} chunks from built-in KB.")
    yield
    logger.info("Shutdown: closing DB connections...")
    await dispose_engine()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="End-to-end RAG Assistant — capstone for 8-week ML/API program.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)


@app.get("/health", tags=["Ops"])
async def health():
    from app.db.database import check_db_connection
    db_ok = await check_db_connection()
    return {"status": "ok", "db": "ok" if db_ok else "error", "index_chunks": index.size}


@app.get("/stats", tags=["Ops"])
async def stats(current_user: User = Depends(get_current_user)):
    """Pipeline health — query metrics, cache state, index size."""
    from app.routers.documents import _jobs
    from app.services.rag import _cache
    return {
        "index": {"chunks": index.size, "unique_docs": len(index.indexed_hashes)},
        "cache": {"entries": len(_cache), "ttl_s": settings.CACHE_TTL_SECONDS, "max": settings.CACHE_MAX_SIZE},
        "queries": metrics.summary(),
        "ingestion_jobs": {
            jid: {k: v for k, v in job.items() if k != "stages"}
            for jid, job in _jobs.items()
        },
    }


@app.get("/eval", tags=["Ops"])
async def eval_endpoint(current_user: User = Depends(get_current_user)):
    """
    Runs the 15-question eval suite against the live system.
    Returns faithfulness, answer_relevancy, and a deployment gate (PASS/BLOCK).
    This is your CI quality gate — run before every deploy.
    Blocks for ~90s on the free Gemini tier (15 RPM limit).
    """
    loop = asyncio.get_event_loop()
    from app.services.eval import run_eval
    result = await loop.run_in_executor(None, run_eval)
    status_code = 200 if result["deployment_gate"] == "PASS" else 424
    return JSONResponse(content=result, status_code=status_code)


@app.get("/", tags=["Ops"])
async def root():
    return {"name": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/docs"}
