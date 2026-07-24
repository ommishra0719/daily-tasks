"""
Chat endpoints.

    POST   /chat/sessions                  -> create a session bound to a named system prompt
    POST   /chat/sessions/{id}/message      -> send a message, stream the reply over SSE
    GET    /chat/sessions/{id}/history      -> full persisted history
    DELETE /chat/sessions/{id}              -> clear a session's history and start fresh
    GET    /chat/prompts                    -> list the named prompt configs users may pick from

Every route requires a valid JWT (`Depends(get_current_user)`) and every
session-scoped route additionally checks that the session belongs to the
calling user -- a session ID from another account returns 404, not 403, so
we don't even confirm that the ID exists to someone who doesn't own it.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.db.models import ChatSession, User
from app.rate_limit import limiter
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.chat import (
    HistoryResponse,
    MessageOut,
    MessageRequest,
    PromptInfo,
    SessionCreateRequest,
    SessionOut,
)
from app.security import get_current_user
from app.services.gemini_service import GeminiService, get_gemini_service
from app.services.prompts import UnknownPromptError, get_system_prompt, list_prompts

logger = logging.getLogger("app.chat")

router = APIRouter(prefix="/chat", tags=["Chat"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_owned_session(
    session_id: str, user: User, db: AsyncSession
) -> ChatSession:
    repo = SessionRepository(db)
    chat_session = await repo.get_by_id(session_id)
    if chat_session is None or chat_session.user_id != user.id:
        # Same response whether the session doesn't exist at all or exists
        # but belongs to someone else -- don't leak which case it is.
        raise HTTPException(status_code=404, detail="Session not found")
    return chat_session


def _trim_context_window(messages: list) -> list[dict]:
    """
    Applies the sliding-window + token-budget trim to a chronological list
    of Message ORM rows, returning plain {"role", "content"} dicts ready to
    hand to the model. Messages are already limited to
    `settings.MAX_CONTEXT_MESSAGES` by the repository query; here we also
    drop further from the front if the cumulative token count of the
    window is still over `settings.MAX_CONTEXT_TOKENS`.
    """
    trimmed = list(messages)

    total_tokens = sum(m.token_count for m in trimmed)
    while total_tokens > settings.MAX_CONTEXT_TOKENS and len(trimmed) > 0:
        dropped = trimmed.pop(0)
        total_tokens -= dropped.token_count

    return [{"role": m.role, "content": m.content} for m in trimmed]


# ---------------------------------------------------------------------------
# Prompt discovery
# ---------------------------------------------------------------------------


@router.get("/prompts", response_model=list[PromptInfo])
async def get_available_prompts(current_user: User = Depends(get_current_user)):
    return [PromptInfo(name=name, description=desc) for name, desc in list_prompts().items()]


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------


@router.post("/sessions", response_model=SessionOut)
async def create_session(
    payload: SessionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        system_prompt = get_system_prompt(payload.prompt_name)
    except UnknownPromptError:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown prompt_name '{payload.prompt_name}'. "
                f"Valid options: {sorted(list_prompts().keys())}"
            ),
        )

    repo = SessionRepository(db)
    chat_session = await repo.create(
        user_id=current_user.id,
        prompt_name=payload.prompt_name,
        system_prompt=system_prompt,
    )

    logger.info(
        "session created | session_id=%s | user=%s | prompt=%s",
        chat_session.id,
        current_user.username,
        chat_session.prompt_name,
    )
    return chat_session


@router.delete("/sessions/{session_id}", response_model=dict)
async def clear_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Clears all persisted messages for this session so the user can start
    fresh, WITHOUT deleting the session itself -- the session keeps its id
    and bound system prompt, so a client can keep using the same session_id
    with an empty transcript rather than provisioning a brand-new one.
    """
    chat_session = await _get_owned_session(session_id, current_user, db)

    message_repo = MessageRepository(db)
    await message_repo.clear_for_session(chat_session.id)

    logger.info("session history cleared | session_id=%s", chat_session.id)
    return {"message": "Session history cleared", "session_id": chat_session.id}


@router.get("/sessions/{session_id}/history", response_model=HistoryResponse)
async def get_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chat_session = await _get_owned_session(session_id, current_user, db)

    message_repo = MessageRepository(db)
    messages = await message_repo.list_for_session(chat_session.id)

    return HistoryResponse(
        session_id=chat_session.id,
        prompt_name=chat_session.prompt_name,
        messages=[MessageOut.model_validate(m) for m in messages],
    )


# ---------------------------------------------------------------------------
# Messaging (SSE streaming)
# ---------------------------------------------------------------------------


async def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@router.post("/sessions/{session_id}/message")
@limiter.limit(settings.RATE_LIMIT_MESSAGE)
async def send_message(
    request: Request,
    session_id: str,
    payload: MessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    gemini: GeminiService = Depends(get_gemini_service),
):
    chat_session = await _get_owned_session(session_id, current_user, db)
    message_repo = MessageRepository(db)

    # 1. Load context BEFORE this turn is added, so the new user message
    #    isn't double-counted in the window.
    recent = await message_repo.last_n_for_session(
        chat_session.id, settings.MAX_CONTEXT_MESSAGES
    )
    context = _trim_context_window(recent)

    # 2. Persist the user's turn immediately -- it's real regardless of
    #    whether the model call below succeeds.
    user_tokens = await gemini.count_tokens(payload.message)
    await message_repo.add(
        session_id=chat_session.id,
        role="user",
        content=payload.message,
        token_count=user_tokens,
    )

    async def event_stream():
        assembled = []
        try:
            async for chunk in gemini.stream_chat(
                system_prompt=chat_session.system_prompt,
                history=context,
                user_message=payload.message,
            ):
                assembled.append(chunk)
                yield await _sse_event({"token": chunk})

            full_text = "".join(assembled)

            # 3. Save the full assembled response to the DB only after the
            #    stream has completely finished sending.
            model_tokens = await gemini.count_tokens(full_text)
            await message_repo.add(
                session_id=chat_session.id,
                role="model",
                content=full_text,
                token_count=model_tokens,
            )

            yield await _sse_event({"done": True})

        except Exception as exc:  # noqa: BLE001
            logger.exception("streaming failed | session_id=%s", chat_session.id)
            yield await _sse_event({"error": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
