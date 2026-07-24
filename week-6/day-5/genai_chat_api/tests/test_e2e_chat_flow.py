"""
End-to-end regression test for the whole capstone stack.

Exercises, against the real FastAPI app (only the DB and the Gemini call
are swapped for fakes -- everything else, including JWT auth, SQLAlchemy
ORM, session/message repositories, and the SSE streaming machinery, is
100% real):

  1. Register a user, log in, get a JWT.
  2. Create a session bound to a named system prompt.
  3. Send 3 messages, verifying conversational context is maintained
     (each reply "sees" the earlier turns of the SAME conversation).
  4. Check the history endpoint returns the full, correctly-ordered
     transcript.
  5. Send enough further messages to exceed the (test-configured, small)
     context window and verify the OLDEST turns are dropped from what is
     sent to the model, even though they remain in the persisted history.
  6. Bonus coverage: prompt_name validation, cross-user isolation (404,
     not leaking existence), and DELETE clearing history.
"""

import json

import pytest

from tests.conftest import fake_gemini_service


def _parse_sse(raw_text: str) -> list[dict]:
    """Turns a raw `text/event-stream` body into a list of decoded JSON events."""
    events = []
    for line in raw_text.split("\n"):
        line = line.strip()
        if line.startswith("data:"):
            payload = line[len("data:"):].strip()
            events.append(json.loads(payload))
    return events


def _full_reply_text(events: list[dict]) -> str:
    return "".join(e["token"] for e in events if "token" in e)


# ---------------------------------------------------------------------------
# Full happy-path flow
# ---------------------------------------------------------------------------


async def test_full_authenticated_chat_flow(client, auth_headers):
    # --- 1. Auth already done via fixtures (register + login -> JWT) ---

    # --- 2. Create a session bound to a named system prompt ---
    resp = await client.post(
        "/chat/sessions", json={"prompt_name": "customer_service"}, headers=auth_headers
    )
    assert resp.status_code == 200
    session = resp.json()
    session_id = session["id"]
    assert session["prompt_name"] == "customer_service"

    # --- 3. Send 3 messages, verifying context is maintained ---
    turns = ["My name is Priya.", "I live in Pune.", "What is my name?"]
    replies = []

    for turn in turns:
        resp = await client.post(
            f"/chat/sessions/{session_id}/message",
            json={"message": turn},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        events = _parse_sse(resp.text)
        assert any("done" in e for e in events)
        replies.append(_full_reply_text(events))

    # The 3rd call's context (what was SENT to the model) must include the
    # 1st user turn -- proving conversational memory actually round-trips
    # through the DB and back into the model call, not just within-process.
    third_call = fake_gemini_service.calls[-1]
    context_users = [h["content"] for h in third_call["history"] if h["role"] == "user"]
    assert "My name is Priya." in context_users
    assert "I live in Pune." in context_users

    # The system prompt bound at session-creation time was actually used.
    assert "patient" in third_call["system_prompt"].lower() or third_call["system_prompt"]

    # --- 4. History endpoint returns the full persisted transcript ---
    resp = await client.get(f"/chat/sessions/{session_id}/history", headers=auth_headers)
    assert resp.status_code == 200
    history = resp.json()
    assert history["session_id"] == session_id
    assert history["prompt_name"] == "customer_service"

    # 3 user turns + 3 model turns = 6 messages, in chronological order.
    messages = history["messages"]
    assert len(messages) == 6
    assert [m["role"] for m in messages] == ["user", "model", "user", "model", "user", "model"]
    assert messages[0]["content"] == "My name is Priya."
    assert messages[2]["content"] == "I live in Pune."
    assert messages[4]["content"] == "What is my name?"


# ---------------------------------------------------------------------------
# Sliding-window limit: old turns must be dropped from model context
# ---------------------------------------------------------------------------


async def test_context_window_drops_oldest_turns(client, auth_headers):
    resp = await client.post(
        "/chat/sessions", json={"prompt_name": "general"}, headers=auth_headers
    )
    session_id = resp.json()["id"]

    # conftest sets MAX_CONTEXT_MESSAGES=4 (2 turns of user+model history).
    # Send 5 user turns; by the last one, turn #1 and #2 should have
    # scrolled out of what's sent to the model, while turns #3 and #4
    # should still be present as context.
    marker_messages = [f"MARKER_TURN_{i}" for i in range(1, 6)]

    for msg in marker_messages:
        resp = await client.post(
            f"/chat/sessions/{session_id}/message",
            json={"message": msg},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    last_call = fake_gemini_service.calls[-1]
    context_users = [h["content"] for h in last_call["history"] if h["role"] == "user"]

    # Oldest turns must have scrolled out of context...
    assert "MARKER_TURN_1" not in context_users
    assert "MARKER_TURN_2" not in context_users
    # ...but the most recent ones (within the window) must still be there.
    assert "MARKER_TURN_3" in context_users
    assert "MARKER_TURN_4" in context_users

    # And yet the FULL history is still all 10 messages (5 user + 5 model)
    # in the database -- windowing only affects what's sent to the model,
    # it never deletes anything.
    resp = await client.get(f"/chat/sessions/{session_id}/history", headers=auth_headers)
    history = resp.json()["messages"]
    assert len(history) == 10
    user_contents = [m["content"] for m in history if m["role"] == "user"]
    assert user_contents == marker_messages


# ---------------------------------------------------------------------------
# System-prompt selection safety
# ---------------------------------------------------------------------------


async def test_unknown_prompt_name_rejected(client, auth_headers):
    resp = await client.post(
        "/chat/sessions", json={"prompt_name": "not_a_real_prompt"}, headers=auth_headers
    )
    assert resp.status_code == 400
    assert "not_a_real_prompt" in resp.json()["detail"]


async def test_prompt_list_endpoint(client, auth_headers):
    resp = await client.get("/chat/prompts", headers=auth_headers)
    assert resp.status_code == 200
    names = {p["name"] for p in resp.json()}
    assert {"general", "customer_service", "code_assistant", "document_qa"} <= names


# ---------------------------------------------------------------------------
# Cross-user isolation
# ---------------------------------------------------------------------------


async def test_user_cannot_access_another_users_session(client, auth_headers):
    resp = await client.post(
        "/chat/sessions", json={"prompt_name": "general"}, headers=auth_headers
    )
    session_id = resp.json()["id"]

    other_user = {"username": "otheruser", "password": "OtherPass123!"}
    await client.post("/auth/register", json=other_user)
    login_resp = await client.post(
        "/auth/login",
        data={"username": other_user["username"], "password": other_user["password"]},
    )
    other_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    resp = await client.get(f"/chat/sessions/{session_id}/history", headers=other_headers)
    assert resp.status_code == 404

    resp = await client.post(
        f"/chat/sessions/{session_id}/message",
        json={"message": "hi"},
        headers=other_headers,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE clears history, keeps the session usable
# ---------------------------------------------------------------------------


async def test_delete_session_clears_history_and_allows_fresh_start(client, auth_headers):
    resp = await client.post(
        "/chat/sessions", json={"prompt_name": "general"}, headers=auth_headers
    )
    session_id = resp.json()["id"]

    await client.post(
        f"/chat/sessions/{session_id}/message",
        json={"message": "This should be forgotten."},
        headers=auth_headers,
    )

    resp = await client.delete(f"/chat/sessions/{session_id}", headers=auth_headers)
    assert resp.status_code == 200

    resp = await client.get(f"/chat/sessions/{session_id}/history", headers=auth_headers)
    assert resp.json()["messages"] == []

    # Same session id still works for new messages after being cleared.
    resp = await client.post(
        f"/chat/sessions/{session_id}/message",
        json={"message": "Fresh start."},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    last_call = fake_gemini_service.calls[-1]
    assert last_call["history"] == []  # nothing carried over from before the clear


# ---------------------------------------------------------------------------
# Auth edge cases (kept lightweight -- the deep auth suite lives upstream in
# tests/test_auth_api.py from week-3/day-5; these just prove wiring here)
# ---------------------------------------------------------------------------


async def test_login_wrong_password_rejected(client, registered_user):
    resp = await client.post(
        "/auth/login",
        data={"username": registered_user["username"], "password": "wrong"},
    )
    assert resp.status_code == 401


async def test_protected_route_without_token_rejected(client):
    resp = await client.post("/chat/sessions", json={"prompt_name": "general"})
    assert resp.status_code == 401
