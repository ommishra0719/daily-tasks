"""
Shared pytest fixtures for the auth API test suite.

Responsible for:
  1. Making the Day-15 auth_api.py module importable (it lives in week-3/day-5
     and reaches into week-4/day-1/app for its db package via a sys.path hack --
     we mirror that here so tests run the SAME code, not a copy of it).
  2. Building an isolated, in-memory async SQLite database that is created
     fresh and torn down after every single test function.
  3. Overriding the app's `get_db` dependency so requests use that isolated
     database instead of the real ./app.db file.
  4. Providing an httpx.AsyncClient wired to the app via ASGITransport (no
     real network socket, no real server process).
"""
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# 0. Workaround for a passlib 1.7.4 + modern bcrypt (>=4.1) incompatibility.
#
#    passlib is unmaintained and, the first time it hashes a password, runs a
#    one-off self-test that verifies a 255-byte dummy secret to check for a
#    decades-old bcrypt "wraparound" bug (long fixed in every backend still
#    in use). Older bcrypt releases silently truncated overlong secrets;
#    bcrypt >=4.1 raises ValueError instead ("password cannot be longer than
#    72 bytes"), which crashes passlib's self-test before your actual
#    password is ever hashed -- this has nothing to do with your app code or
#    your test's password length. Telling passlib the self-test already
#    passed skips that dead code path entirely and is safe, since the bug
#    it was checking for does not exist in any bcrypt version anyone still
#    installs.
# ---------------------------------------------------------------------------
try:
    from passlib.handlers.bcrypt import _BcryptBackend
    _BcryptBackend._workrounds_initialized = True
except ImportError:
    pass

# ---------------------------------------------------------------------------
# 1. Put BOTH source folders on sys.path ourselves, explicitly, before
#    importing anything.
#
#    auth_api.py lives in week-3/day-5/ and its `db` package (database.py,
#    models.py, repository.py) lives in week-4/day-1/app/ -- two completely
#    different folders, neither of which is anywhere near tests/. We must
#    not rely on auth_api.py's own internal sys.path hack to make `db`
#    importable for US, because that only works by accident (only after
#    auth_api has already been imported once, and only if its relative
#    path math matches our folder layout). We add both paths ourselves so
#    this works regardless of import order or how pytest is invoked.
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent  # tests/ -> repo root

AUTH_API_DIR = REPO_ROOT / "week-3" / "day-5"
DB_PACKAGE_DIR = REPO_ROOT / "week-4" / "day-1" / "app"

for _path in (AUTH_API_DIR, DB_PACKAGE_DIR):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

from auth_api import app  # noqa: E402  (safe now: both dirs are on sys.path)
from db.database import Base, get_db  # noqa: E402  (same module auth_api uses)

# ---------------------------------------------------------------------------
# 2. Isolated in-memory test database.
# ---------------------------------------------------------------------------
# StaticPool is what makes an in-memory SQLite DB usable across multiple
# async connections/sessions within the same test: normally every new
# connection to ":memory:" gets its OWN empty database. StaticPool forces
# SQLAlchemy to reuse a single underlying connection so tables created at
# the start of a test are still there for the rest of that test.
TEST_DATABASE_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    expire_on_commit=False,
)


async def _override_get_db():
    """Replacement for the real get_db dependency, used only in tests."""
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture(autouse=True)
async def reset_db():
    """
    Runs before AND after every test (autouse=True, scope='function' by
    default). Creates all tables fresh, yields control to the test, then
    drops everything -- guaranteeing zero state leakage between tests.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def override_dependencies():
    """
    Installs the dependency override for the duration of a test and
    guarantees cleanup afterwards, even if the test raises.
    """
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client(override_dependencies):
    """An httpx.AsyncClient talking directly to the ASGI app, no server."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_user():
    """One consistent, reusable set of test credentials."""
    return {"username": "testuser", "password": "SecurePass123!"}


@pytest.fixture
async def registered_user(client, test_user):
    """Registers `test_user` and returns its credentials."""
    resp = await client.post("/auth/register", json=test_user)
    assert resp.status_code == 200
    return test_user


@pytest.fixture
async def auth_headers(client, registered_user):
    """
    Logs the already-registered test user in and returns a ready-to-use
    Authorization header dict, so protected-route tests don't repeat the
    login dance every time.
    """
    resp = await client.post(
        "/auth/login",
        data={
            "username": registered_user["username"],
            "password": registered_user["password"],
        },
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}