"""
Shared pytest fixtures for the capstone's end-to-end test suite.

Responsible for:
  1. Working around a passlib 1.7.4 + modern bcrypt incompatibility (a
     one-off self-test passlib runs on first hash, unrelated to app code).
  2. Building an isolated in-memory async SQLite database, created fresh
     and torn down for every single test function so nothing leaks
     between tests and nothing depends on execution order.
  3. Overriding `get_db` so requests use that isolated database instead of
     the real ./genai_chat.db file.
  4. Overriding `get_gemini_service` with an in-memory `FakeGeminiService`
     so the whole suite runs with no network access and no API key --
     it deterministically "answers" using the history and system prompt
     it was given, which is exactly what lets the tests *prove* that
     context is maintained and that the sliding window drops old turns.
  5. Providing an httpx.AsyncClient wired to the app via ASGITransport.
"""

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# 0. passlib / bcrypt self-test workaround (see week-3 conftest for the
#    original discovery of this issue -- harmless, skips a dead code path).
# ---------------------------------------------------------------------------
try:
    from passlib.handlers.bcrypt import _BcryptBackend

    _BcryptBackend._workrounds_initialized = True
except ImportError:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.config import settings  # noqa: E402
from app.db.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.gemini_service import get_gemini_service  # noqa: E402

# ---------------------------------------------------------------------------
# Test-time settings: a small context window so the "window limit" test
# doesn't need dozens of messages to prove the point.
# ---------------------------------------------------------------------------
settings.MAX_CONTEXT_MESSAGES = 4  # 2 user/model turns of context
settings.MAX_CONTEXT_TOKENS = 100_000  # large enough to not interfere here
settings.RATE_LIMIT_MESSAGE = "1000/minute"
settings.RATE_LIMIT_AUTH = "1000/minute"

# ---------------------------------------------------------------------------
# Isolated in-memory test database (StaticPool keeps one connection alive
# across the whole test so tables created at setup are still there later).
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)


async def _override_get_db():
    async with TestingSessionLocal() as session:
        yield session


class FakeGeminiService:
    """
    Deterministic stand-in for the real Gemini API.

    Instead of generating novel text, it reports back exactly what it was
    given: the system prompt (truncated) and every user turn currently in
    its `history` argument, plus the new message. This makes it possible to
    assert, from the OUTSIDE (via the model's reply text), whether a given
    earlier user message was or wasn't present in the context sent to the
    model -- which is exactly what the window-limit test needs to check.
    """

    def __init__(self):
        self.calls: list[dict] = []

    async def count_tokens(self, text: str) -> int:
        # Simple, deterministic, offline stand-in for real token counting.
        return max(1, len(text.split()))

    async def stream_chat(self, system_prompt: str, history: list[dict], user_message: str):
        self.calls.append(
            {"system_prompt": system_prompt, "history": history, "user_message": user_message}
        )

        history_users = [h["content"] for h in history if h["role"] == "user"]
        reply = (
            f"REPLY_TO={user_message} | "
            f"SYSTEM={system_prompt[:20]} | "
            f"CONTEXT_USERS=[{'|'.join(history_users)}]"
        )
        for word in reply.split(" "):
            yield word + " "


fake_gemini_service = FakeGeminiService()


def _get_fake_gemini_service():
    return fake_gemini_service


@pytest.fixture(autouse=True)
async def reset_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    fake_gemini_service.calls.clear()


@pytest.fixture
def override_dependencies():
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_gemini_service] = _get_fake_gemini_service
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_user():
    return {"username": "testuser", "password": "SecurePass123!"}


@pytest.fixture
async def registered_user(client, test_user):
    resp = await client.post("/auth/register", json=test_user)
    assert resp.status_code == 200
    return test_user


@pytest.fixture
async def auth_headers(client, registered_user):
    resp = await client.post(
        "/auth/login",
        data={
            "username": registered_user["username"],
            "password": registered_user["password"],
        },
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
