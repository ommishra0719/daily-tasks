"""
Chat endpoints — SSE streaming RAG responses with citations.
Composed from week-6/day-5 session/history pattern + week-8/day-1 RAG chain.
"""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import ChatSession, Message, User
from app.schemas import HistoryResponse, MessageOut, MessageRequest, SessionCreate, SessionOut
from app.security import get_current_user
from app.services.rag import rag_query_stream

logger = logging.getLogger("chat")
router = APIRouter(prefix="/chat", tags=["Chat"])


async def _owned_session(session_id: str, user: User, db: AsyncSession) -> ChatSession:
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    s = result.scalar_one_or_none()
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    return s


@router.post("/sessions", response_model=SessionOut, status_code=201)
async def create_session(
    payload: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    s = ChatSession(user_id=current_user.id, title=payload.title)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@router.get("/sessions/{session_id}/history", response_model=HistoryResponse)
async def get_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    s = await _owned_session(session_id, current_user, db)
    result = await db.execute(
        select(Message).where(Message.session_id == s.id).order_by(Message.created_at)
    )
    messages = result.scalars().all()
    return HistoryResponse(
        session_id=s.id,
        messages=[MessageOut.model_validate(m) for m in messages],
    )


@router.post("/sessions/{session_id}/message")
async def send_message(
    session_id: str,
    payload: MessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    SSE streaming RAG response.
    Each event is a JSON object:
      {"token": "..."} during streaming
      {"citations": [...], "cache_hit": bool, "done": true} at the end
    """
    s = await _owned_session(session_id, current_user, db)

    # Load recent history for context (last 10 messages)
    result = await db.execute(
        select(Message)
        .where(Message.session_id == s.id)
        .order_by(Message.created_at.desc())
        .limit(10)
    )
    recent = list(reversed(result.scalars().all()))
    history = [{"role": m.role, "content": m.content} for m in recent]

    # Persist user message
    user_msg = Message(session_id=s.id, role="user", content=payload.message, citations="[]")
    db.add(user_msg)
    await db.commit()

    async def event_stream():
        assembled_tokens = []
        citations = []
        try:
            async for raw in rag_query_stream(payload.message, history):
                event = json.loads(raw)
                if "token" in event:
                    assembled_tokens.append(event["token"])
                if event.get("done"):
                    citations = event.get("citations", [])
                yield f"data: {raw}\n\n"

            # Persist assistant response
            full_answer = "".join(assembled_tokens).strip()
            asst_msg = Message(
                session_id=s.id,
                role="assistant",
                content=full_answer,
                citations=json.dumps(citations),
            )
            db.add(asst_msg)
            await db.commit()

        except Exception as exc:
            logger.exception("stream failed | session=%s", session_id)
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
