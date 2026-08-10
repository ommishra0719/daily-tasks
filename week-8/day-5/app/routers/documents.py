"""
Document ingestion — async background task with SSE progress stream.
Composed from week-8/day-4 _run_ingestion pattern + week-6/day-5 JWT auth.
"""
import asyncio
import hashlib
import json
import logging
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Document, User
from app.schemas import IngestRequest, IngestResponse
from app.security import get_current_user
from app.services.rag import chunk_text, index

logger = logging.getLogger("documents")
router = APIRouter(prefix="/documents", tags=["Documents"])

# In-memory job registry (fine for single-process; use Redis for multi-worker)
_jobs: dict = {}


async def _run_ingestion(job_id: str, documents: list, owner_id: int, db: AsyncSession):
    """4-stage pipeline: LOAD → CLEAN/DEDUP → CHUNK → INDEX (from week-8/day-4)."""
    import time
    job = _jobs[job_id]
    job["status"] = "running"
    t0 = time.time()

    def stage(name: str, detail: str = ""):
        entry = {"stage": name, "t": round(time.time() - t0, 3), "detail": detail}
        job["stages"].append(entry)
        logger.info(f"[{job_id}] {name} — {detail}")

    stage("LOAD", f"{len(documents)} document(s) received")
    await asyncio.sleep(0)

    new_docs = []
    for doc in documents:
        content_hash = hashlib.md5(doc["text"].encode()).hexdigest()
        if content_hash in index.indexed_hashes:
            stage("SKIP", f"'{doc.get('filename', doc.get('id', '?'))}' already indexed")
            continue
        index.indexed_hashes.add(content_hash)
        new_docs.append({
            "id": doc.get("id", str(uuid.uuid4())[:8]),
            "filename": doc.get("filename", doc.get("id", "unknown")),
            "text": " ".join(doc["text"].split()),
            "hash": content_hash,
        })

    stage("CLEAN", f"{len(new_docs)} new document(s) after dedup")
    await asyncio.sleep(0)

    total_chunks = 0
    for doc in new_docs:
        chunks = chunk_text(doc["text"])
        index.add(chunks, doc["filename"])
        total_chunks += len(chunks)

        # Persist to DB
        db_doc = Document(
            id=doc["id"],
            owner_id=owner_id,
            filename=doc["filename"],
            content_hash=doc["hash"],
            chunk_count=len(chunks),
            indexed=True,
        )
        db.add(db_doc)

    await db.commit()
    stage("INDEX", f"{total_chunks} chunks added — index now {index.size} chunks total")
    job["status"] = "done"
    job["doc_count"] = len(new_docs)
    job["chunk_count"] = total_chunks


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    payload: IngestRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not payload.documents:
        return JSONResponse({"error": "no documents"}, status_code=400)

    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {"status": "queued", "stages": [], "doc_count": 0, "chunk_count": 0}
    background_tasks.add_task(_run_ingestion, job_id, payload.documents, current_user.id, db)

    return IngestResponse(job_id=job_id, status="queued", queued_count=len(payload.documents))


@router.get("/ingest/{job_id}/status")
async def ingest_status(job_id: str, current_user: User = Depends(get_current_user)):
    """GET for simple polling; also see /ingest/{job_id}/progress for SSE."""
    if job_id not in _jobs:
        return JSONResponse({"error": "job not found"}, status_code=404)
    job = _jobs[job_id]
    return {k: v for k, v in job.items() if k != "stages"}


@router.get("/ingest/{job_id}/progress")
async def ingest_progress(job_id: str, current_user: User = Depends(get_current_user)):
    """SSE stream of stage-by-stage ingestion progress (from week-8/day-4)."""
    if job_id not in _jobs:
        return JSONResponse({"error": "job not found"}, status_code=404)

    async def stream() -> AsyncGenerator[str, None]:
        seen = 0
        while True:
            job = _jobs[job_id]
            while seen < len(job["stages"]):
                yield f"data: {json.dumps(job['stages'][seen])}\n\n"
                seen += 1
            if job["status"] == "done":
                yield f"data: {json.dumps({'stage': 'DONE', 'doc_count': job['doc_count'], 'chunk_count': job['chunk_count']})}\n\n"
                break
            await asyncio.sleep(0.1)

    return StreamingResponse(stream(), media_type="text/event-stream")
