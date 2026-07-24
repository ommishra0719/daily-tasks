"""
Thin wrapper around the Gemini API used by the chat endpoint.

Kept deliberately small and behind a simple interface (`count_tokens`,
`stream_chat`) so the router never touches the `google-genai` SDK directly.
That makes the router trivially testable: `tests/conftest.py` overrides the
`get_gemini_service` dependency with an in-memory fake that needs no
network access and no API key, so the full auth -> session -> message ->
history flow can be exercised in CI without ever calling Google.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator, Protocol

from app.config import settings

logger = logging.getLogger("app.gemini")


class MessageTurn(Protocol):
    role: str  # "user" | "model"
    content: str


class GeminiService:
    """Protocol-ish base class documenting the interface routers rely on."""

    async def count_tokens(self, text: str) -> int:  # pragma: no cover - interface
        raise NotImplementedError

    async def stream_chat(
        self,
        system_prompt: str,
        history: list[dict],
        user_message: str,
    ) -> AsyncGenerator[str, None]:  # pragma: no cover - interface
        raise NotImplementedError
        yield ""  # noqa - makes this an async generator for type-checkers


class LiveGeminiService(GeminiService):
    """Real implementation, backed by the google-genai SDK."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        api_key = api_key or settings.GEMINI_API_KEY
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured. Set it in your environment "
                "or .env file before sending chat messages."
            )

        # Imported lazily so the whole app (and its test suite) can run
        # without the google-genai package's transitive deps being an
        # issue for environments that only exercise the fake service.
        from google import genai

        self._genai = genai
        self.client = genai.Client(api_key=api_key)
        self.model = model or settings.GEMINI_MODEL

    def _build_contents(self, history: list[dict], user_message: str):
        from google.genai import types

        contents = [
            types.Content(role=turn["role"], parts=[types.Part.from_text(text=turn["content"])])
            for turn in history
        ]
        contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=user_message)])
        )
        return contents

    async def count_tokens(self, text: str) -> int:
        if not text.strip():
            return 0
        response = await self.client.aio.models.count_tokens(
            model=self.model,
            contents=text,
        )
        return response.total_tokens

    async def stream_chat(
        self,
        system_prompt: str,
        history: list[dict],
        user_message: str,
    ) -> AsyncGenerator[str, None]:
        from google.genai import types

        config = types.GenerateContentConfig(system_instruction=system_prompt)
        contents = self._build_contents(history, user_message)

        stream = await self.client.aio.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=config,
        )
        async for chunk in stream:
            try:
                text = chunk.text or ""
            except ValueError:
                text = ""
            if text:
                yield text


_service_singleton: GeminiService | None = None


def get_gemini_service() -> GeminiService:
    """
    FastAPI dependency. Lazily builds a single LiveGeminiService instance
    per process (constructing the SDK client is not free). Overridden in
    tests via `app.dependency_overrides[get_gemini_service] = ...`.
    """
    global _service_singleton
    if _service_singleton is None:
        _service_singleton = LiveGeminiService()
    return _service_singleton
