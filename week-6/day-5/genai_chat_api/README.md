# GenAI Capstone — Authenticated Streaming Chat API

A full-stack integration of everything from Phase 2 (FastAPI fundamentals,
async SQLAlchemy, JWT auth, rate limiting, middleware) and Phase 3 (Gemini
API, streaming, conversation memory, prompt management) into one
production-shaped service:

**Auth (JWT) → Sessions (system prompt binding) → Streaming chat (SSE) →
Persisted history → Windowed context.**

---

## 1. Architecture

```
┌──────────┐   1. POST /auth/register            ┌─────────────┐
│  Client  │──────────────────────────────────▶  │  Auth        │
│          │   2. POST /auth/login  (JWT out)     │  router      │
└────┬─────┘◀──────────────────────────────────  └──────┬──────┘
     │                                                    │
     │  Authorization: Bearer <JWT>                       │ passlib (bcrypt)
     │                                                    ▼
     │                                             ┌─────────────┐
     │  3. POST /chat/sessions {prompt_name}        │  users table │
     │───────────────────────────────────────────▶  └─────────────┘
     │        looks up prompt_name in prompts.yaml
     │        creates ChatSession row (id, system_prompt snapshot)
     │◀─────────────────────────────────────────── {session_id}
     │
     │  4. POST /chat/sessions/{id}/message {message}
     │───────────────────────────────────────────▶ ┌────────────────────┐
     │                                              │ Chat router         │
     │                                              │  a) verify JWT      │
     │                                              │  b) verify ownership│
     │                                              │  c) load last N     │
     │                                              │     messages (DB)   │
     │                                              │  d) persist user msg│
     │                                              │  e) call Gemini,    │
     │                                              │     stream chunks   │
     │◀═══ SSE: data: {"token": "..."} ════════════ │  f) persist full    │
     │◀═══ SSE: data: {"done": true}   ════════════ │     assembled reply │
     │                                              └──────────┬─────────┘
     │                                                          │
     │  5. GET /chat/sessions/{id}/history                      ▼
     │───────────────────────────────────────────▶      ┌───────────────┐
     │◀─────────────────────────────── full transcript  │ SQLite (async) │
     │                                                    │ users          │
     │  6. DELETE /chat/sessions/{id}  (clear history)    │ chat_sessions  │
     │───────────────────────────────────────────▶       │ messages       │
     └─────────────────────────────────────────────────  └───────────────┘
```

### Request lifecycle for a message

1. **JWT validation** (`get_current_user` dependency) — every chat route
   requires `Authorization: Bearer <token>`.
2. **Ownership check** (`_get_owned_session`) — a session ID belonging to
   another user returns `404`, never `403`, so existence isn't leaked.
3. **Context load** — the last `MAX_CONTEXT_MESSAGES` messages are pulled
   from the DB (oldest of that slice first), then trimmed further by
   cumulative `token_count` if still over `MAX_CONTEXT_TOKENS`.
4. **User turn persisted immediately** — it's real regardless of whether
   the model call below succeeds.
5. **Gemini streamed** — `system_prompt` (bound at session-creation time)
   + trimmed history + new message are sent to Gemini; tokens stream back
   over Server-Sent Events (`text/event-stream`) as they're generated.
6. **Full reply persisted after the stream finishes** — the client sees
   tokens as they arrive, but the DB only gets one clean `Message` row
   for the complete assistant turn, once the stream is done.

---

## 2. Project layout

```
genai_chat_api/
├── app/
│   ├── main.py                # FastAPI app, lifespan, middleware, routers
│   ├── config.py              # pydantic-settings, single source of truth
│   ├── security.py            # password hashing, JWT issue/verify, get_current_user
│   ├── middleware.py           # request logging + per-user rate-limit key
│   ├── rate_limit.py           # shared slowapi Limiter instance
│   ├── prompts.yaml            # NAMED system prompt configs (no free text)
│   ├── db/
│   │   ├── database.py         # async engine/session, init/dispose
│   │   └── models.py           # User, ChatSession, Message (SQLAlchemy ORM)
│   ├── repositories/           # DB access, one class per aggregate
│   │   ├── user_repository.py
│   │   ├── session_repository.py
│   │   └── message_repository.py
│   ├── schemas/                # pydantic request/response models
│   │   ├── auth.py
│   │   └── chat.py
│   ├── services/
│   │   ├── gemini_service.py   # Gemini SDK wrapper (streaming + token count)
│   │   └── prompts.py          # loads/validates prompts.yaml, by-name lookup
│   └── routers/
│       ├── auth.py              # /auth/register, /auth/login, /auth/me
│       ├── chat.py              # /chat/sessions, /message (SSE), /history, DELETE
│       └── health.py            # /health/live, /health/ready
├── tests/
│   ├── conftest.py              # isolated DB + FakeGeminiService fixtures
│   └── test_e2e_chat_flow.py    # full regression suite (see below)
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── .env.example
└── README.md
```

---

## 3. Design decisions & how they map to the brief

| Requirement | Implementation |
|---|---|
| **Session storage** | `ChatSession(id, user_id, prompt_name, system_prompt, created_at)` + `Message(id, session_id, role, content, token_count, created_at)`, exactly the schema from the brief (plus `token_count` for windowing). |
| **System prompt management** | Named configs live in `app/prompts.yaml`, loaded once via `app/services/prompts.py`. `POST /chat/sessions` takes `prompt_name` only — **there is no code path that accepts raw system-prompt text from a user.** The resolved prompt text is *snapshotted* onto the session row at creation time, so editing `prompts.yaml` later never silently changes an existing session's behaviour. |
| **Log history + system prompt together** | Every session row stores its own `system_prompt` snapshot; every message row is tied to `session_id`. A `GET .../history` call reconstructs the full picture — prompt + transcript — for any session. |
| **Stream + persist after completion** | `send_message`'s `event_stream()` generator accumulates chunks in a list, and only calls `message_repo.add(role="model", ...)` **after** the `async for` loop over Gemini's stream finishes. |
| **DELETE to clear history** | `DELETE /chat/sessions/{id}` deletes all `Message` rows for that session but keeps the `ChatSession` row (and its bound prompt) — the same `session_id` can keep being used with a blank transcript. This is a judgment call; see the docstring on `clear_session` if you'd rather delete the whole session instead. |
| **Rate limit per user, not per IP** | `app/middleware.py:rate_limit_key` reads the `Authorization` header, decodes the JWT's `sub` claim (signature-checked, expiry ignored — it's only a rate-limit bucket key, not an auth decision), and buckets on `user:<username>`. Falls back to IP only for unauthenticated calls like `/auth/login`. |
| **Integration test** | `tests/test_e2e_chat_flow.py::test_full_authenticated_chat_flow` does register → login → create session → 3 messages verifying context → history check, in one test. The window-limit scenario is its own test, `test_context_window_drops_oldest_turns`. |

---

## 4. Setup

```bash
cd genai_chat_api
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

pip install -r requirements-dev.txt   # includes prod deps + pytest/httpx

cp .env.example .env
# Edit .env and set:
#   SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
#   GEMINI_API_KEY=<your key from https://aistudio.google.com/apikey>

uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for interactive Swagger UI.

### Running the tests

```bash
pytest -v
```

The test suite **never calls the real Gemini API or hits a real database
file** — `tests/conftest.py` overrides `get_db` with an in-memory SQLite
database and overrides `get_gemini_service` with a deterministic
`FakeGeminiService` that echoes back exactly what context/system-prompt it
was given. That's what lets the tests *prove* (not just hope) that
conversation context round-trips through the database correctly, and that
the sliding window actually drops the oldest turns once it fills up.

---

## 5. API walkthrough

```bash
# 1. Register
curl -X POST localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "SecurePass123!"}'

# 2. Login -> JWT
TOKEN=$(curl -s -X POST localhost:8000/auth/login \
  -d "username=alice&password=SecurePass123!" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 3. See available system prompts
curl localhost:8000/chat/prompts -H "Authorization: Bearer $TOKEN"

# 4. Create a session
SESSION_ID=$(curl -s -X POST localhost:8000/chat/sessions \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"prompt_name": "code_assistant"}' | python -c "import sys,json;print(json.load(sys.stdin)['id'])")

# 5. Send a message, stream the SSE reply
curl -N -X POST localhost:8000/chat/sessions/$SESSION_ID/message \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"message": "How do I reverse a linked list in Python?"}'

# 6. Get full history
curl localhost:8000/chat/sessions/$SESSION_ID/history -H "Authorization: Bearer $TOKEN"

# 7. Clear the session and start fresh
curl -X DELETE localhost:8000/chat/sessions/$SESSION_ID -H "Authorization: Bearer $TOKEN"
```

---

## 6. Known limitations / next steps

- **SQLite** is fine for a demo; swap `DATABASE_URL` for Postgres
  (`postgresql+asyncpg://...`) for anything multi-instance, since SQLite
  doesn't handle concurrent writers well.
- **Rate limiting is in-process** (slowapi's default in-memory backend) —
  fine for a single instance; use its Redis backend once you run more than
  one worker/replica so all instances share one bucket.
- **No `summary_cache` column yet** — the brief flags this as a
  later-add for long-running sessions that need LLM-based summarization
  instead of a hard sliding window (see `week-6/day-2/chat_session.py` in
  this repo for a prior prototype of that pattern).
- **JWTs aren't revocable** — there's no denylist/refresh-token rotation;
  fine for a demo, not for production as-is.
