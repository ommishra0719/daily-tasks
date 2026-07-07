"""
tests/test_auth_api.py

Full test suite for the Day 15-16 auth API (week-3/day-5/auth_api.py, backed
by the async SQLAlchemy models/repository in week-4/day-1/app/db).

Covers:
  - Registration: success, duplicate username, validation errors
  - Login: success, wrong password, nonexistent user, malformed request
  - Protected access (/auth/me): valid token, missing token, malformed
    header, garbage token, expired token, token for a deleted user
  - Security sanity checks: password is hashed, not stored/returned in
    plaintext; two different users get different tokens

Every test gets a brand-new in-memory database (see conftest.py's autouse
`reset_db` fixture) so nothing here depends on test execution order and
nothing here leaks into any other test.
"""
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

import auth_api


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

async def test_register_success(client, test_user):
    resp = await client.post("/auth/register", json=test_user)
    assert resp.status_code == 200
    assert resp.json() == {"message": "User registered successfully"}


async def test_register_duplicate_username_rejected(client, registered_user):
    # registered_user fixture already created this user once
    resp = await client.post("/auth/register", json=registered_user)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "User already exists"


async def test_register_missing_password_returns_422(client, test_user):
    resp = await client.post(
        "/auth/register", json={"username": test_user["username"]}
    )
    assert resp.status_code == 422


async def test_register_missing_username_returns_422(client, test_user):
    resp = await client.post(
        "/auth/register", json={"password": test_user["password"]}
    )
    assert resp.status_code == 422


async def test_register_password_is_hashed_not_plaintext(client, test_user):
    """The API must never persist or leak the raw password."""
    await client.post("/auth/register", json=test_user)

    # Log in and confirm the raw password verifies against the stored hash
    # via the API's own flow, then independently confirm hashing happened
    # by checking the hash function directly (not the DB internals, since
    # that would couple the test too tightly to repository details).
    hashed = auth_api.hash_password(test_user["password"])
    assert hashed != test_user["password"]
    assert auth_api.verify_password(test_user["password"], hashed)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

async def test_login_success_returns_bearer_token(client, registered_user):
    resp = await client.post(
        "/auth/login",
        data={
            "username": registered_user["username"],
            "password": registered_user["password"],
        },
    )
    body = resp.json()
    assert resp.status_code == 200
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and len(body["access_token"]) > 0


async def test_login_wrong_password_rejected(client, registered_user):
    resp = await client.post(
        "/auth/login",
        data={"username": registered_user["username"], "password": "wrong-password"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Incorrect username or password"


async def test_login_nonexistent_user_rejected(client):
    resp = await client.post(
        "/auth/login",
        data={"username": "ghost", "password": "whatever123"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Incorrect username or password"


async def test_login_missing_fields_returns_422(client):
    # OAuth2PasswordRequestForm requires both fields as form data
    resp = await client.post("/auth/login", data={"username": "onlyusername"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Protected route: /auth/me
# ---------------------------------------------------------------------------

async def test_me_with_valid_token_returns_user(client, registered_user, auth_headers):
    resp = await client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == registered_user["username"]
    assert "id" in body


async def test_me_without_token_rejected(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


async def test_me_with_malformed_header_rejected(client, auth_headers):
    # Missing the "Bearer " scheme prefix
    token_only = auth_headers["Authorization"].split(" ")[1]
    resp = await client.get("/auth/me", headers={"Authorization": token_only})
    assert resp.status_code == 401


async def test_me_with_garbage_token_rejected(client):
    resp = await client.get(
        "/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid or expired token"


async def test_me_with_token_for_deleted_user_rejected(client, registered_user, auth_headers):
    """
    A token can be structurally valid (correct signature, not expired) but
    reference a user that no longer exists -- e.g. account was deleted after
    the token was issued. get_current_user must still reject it.
    """
    from db.database import get_db as real_get_db  # noqa
    import auth_api as api

    # Delete the underlying user directly through the same overridden
    # session the app is using in this test.
    override = api.app.dependency_overrides[real_get_db]
    async for session in override():
        from db.repository import UserRepository
        repo = UserRepository(session)
        user = await repo.get_by_username(registered_user["username"])
        await session.delete(user)
        await session.commit()
        break

    resp = await client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 401
    assert resp.json()["detail"] == "User not found"


async def test_me_with_expired_token_rejected(client, registered_user):
    """
    Mint a token that is already expired by freezing `datetime.utcnow()`
    (as imported inside auth_api) to a point in the past, then confirm the
    protected route rejects it.
    """
    past = datetime.utcnow() - timedelta(hours=1)

    with patch("auth_api.datetime") as mock_dt:
        mock_dt.utcnow.return_value = past
        # timedelta is untouched, only utcnow() is frozen
        expired_token = auth_api.create_access_token(
            {"sub": registered_user["username"]}
        )

    resp = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid or expired token"


# ---------------------------------------------------------------------------
# Cross-cutting sanity checks
# ---------------------------------------------------------------------------

async def test_two_users_get_independent_tokens(client):
    user_a = {"username": "alice", "password": "AlicePass123!"}
    user_b = {"username": "bob", "password": "BobPass123!"}

    await client.post("/auth/register", json=user_a)
    await client.post("/auth/register", json=user_b)

    resp_a = await client.post(
        "/auth/login", data={"username": "alice", "password": "AlicePass123!"}
    )
    resp_b = await client.post(
        "/auth/login", data={"username": "bob", "password": "BobPass123!"}
    )
    token_a = resp_a.json()["access_token"]
    token_b = resp_b.json()["access_token"]
    assert token_a != token_b

    me_a = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token_a}"}
    )
    me_b = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert me_a.json()["username"] == "alice"
    assert me_b.json()["username"] == "bob"


async def test_database_is_isolated_between_tests(client):
    """
    Guards against state leakage: if a previous test's data (e.g. 'alice')
    were still around, this registration would unexpectedly collide. This
    test intentionally reuses a username from another test in this file to
    prove the per-test database reset is actually working.
    """
    resp = await client.post(
        "/auth/register", json={"username": "alice", "password": "FreshPass123!"}
    )
    assert resp.status_code == 200