from __future__ import annotations

import json
import logging
import os
import time
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from google import genai
from pydantic import BaseModel, Field

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY is not configured.")

client = genai.Client(api_key=api_key)

MODEL_NAME = "gemini-2.5-flash"

app = FastAPI(title="Streaming Gemini Chat API")

# -------------------------------------------------------------------
# Request Model
# -------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)


# -------------------------------------------------------------------
# Streaming Generator
# -------------------------------------------------------------------


async def stream_response(
    message: str,
    session_id: str,
) -> AsyncGenerator[str, None]:
    """
    Stream Gemini output as Server-Sent Events.
    """

    start = time.perf_counter()
    chunk_count = 0

    logger.info("Stream started | session=%s", session_id)

    try:
        async for chunk in await client.aio.models.generate_content_stream(
            model=MODEL_NAME,
            contents=message,
        ):
            # Safe text extraction: Handles metadata/empty chunks without crashing
            try:
                text = chunk.text or ""
            except ValueError:
                text = ""

            if not text:
                continue

            chunk_count += 1

            yield (
                f"data: {json.dumps({'token': text})}\n\n"
            )

        yield "data: [DONE]\n\n"

    except Exception as exc:

        logger.exception("Streaming failed")

        yield (
            f"data: {json.dumps({'error': str(exc)})}\n\n"
        )

    finally:

        duration = time.perf_counter() - start

        logger.info(
            "Stream ended | session=%s | duration=%.2fs | chunks=%d",
            session_id,
            duration,
            chunk_count,
        )


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------


@app.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
) -> StreamingResponse:
    """
    Stream Gemini responses over Server-Sent Events.
    """

    if not request.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    return StreamingResponse(
        stream_response(
            request.message,
            request.session_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "status": "Streaming API is running."
    }