# RAG Assistant — 8-Week Capstone

End-to-end Retrieval-Augmented Generation API. Built over 8 weeks: FastAPI, JWT auth, BM25 retrieval, Gemini generation, SSE streaming, TTL caching, async ingestion, and a continuous eval suite.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client (curl / browser)                  │
└────────────┬──────────────┬─────────────────┬───────────────────┘
             │              │                 │
      POST /auth/*   POST /documents/   POST /chat/sessions/
      (register,     ingest             {id}/message
       login)        (JWT protected)    (JWT protected, SSE)
             │              │                 │
┌────────────▼──────────────▼─────────────────▼───────────────────┐
│                         FastAPI App                              │
│                                                                  │
│   ┌──────────┐   ┌───────────────────┐   ┌──────────────────┐   │
│   │Auth Router│   │Documents Router   │   │Chat Router       │   │
│   │ /register │   │ /ingest           │   │ /sessions        │   │
│   │ /login    │   │ /ingest/{id}/     │   │ /{id}/message    │   │
│   │ /me       │   │   status|progress │   │ /{id}/history    │   │
│   └─────┬─────┘   └────────┬──────────┘   └────────┬─────────┘   │
│         │                  │                        │             │
│   ┌─────▼──────────────────▼────────────────────────▼─────────┐  │
│   │                   RAG Service (app/services/rag.py)        │  │
│   │                                                            │  │
│   │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐  │  │
│   │  │ BM25 Index  │  │  TTL Cache  │  │  Gemini Client   │  │  │
│   │  │ (in-memory) │  │ (5min, 256) │  │  (w/ 429 retry)  │  │  │
│   │  └──────┬──────┘  └──────┬──────┘  └────────┬─────────┘  │  │
│   │         │  Multi-query   │ Cache hit          │ Generate   │  │
│   │         │  (3 variants)  │ → skip retrieval   │ answer     │  │
│   │         └────────────────┴────────────────────┘           │  │
│   └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│   ┌────────────────────────────────────────────────────────────┐  │
│   │              SQLite (SQLAlchemy async)                     │  │
│   │   users │ documents │ chat_sessions │ messages             │  │
│   └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│   ┌──────────────────────┐  ┌─────────────────────────────────┐  │
│   │  /stats (metrics)    │  │  /eval (quality gate)           │  │
│   │  query_count, p50,   │  │  15 questions, faithfulness +   │  │
│   │  p95, cache_hit_rate │  │  relevancy, PASS/BLOCK result   │  │
│   └──────────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                    │
                          ┌─────────▼────────┐
                          │  Gemini API       │
                          │  gemini-2.0-      │
                          │  flash-lite       │
                          │  (generation +    │
                          │   LLM-as-judge)   │
                          └──────────────────┘
```

**Component choices:**
- **BM25 over Qdrant/ChromaDB** — no external service needed to run locally; swap `Index.retrieve()` for a Qdrant client call to scale to millions of chunks without changing any other code.
- **SQLite over Postgres** — zero-dependency local dev; `DATABASE_URL` is the only change needed for production.
- **SSE over WebSockets** — SSE is HTTP/1.1 compatible, stateless, works through proxies and load balancers without sticky sessions, and is sufficient for server→client token streaming.
- **In-process TTL cache over Redis** — fine for single-worker deployments; swap `TTLCache` for a Redis client when scaling horizontally.

---

## Skills from each week

| Week | What it contributes |
|------|---------------------|
| 1 | Type hints, decorators, async patterns throughout |
| 2 | Chunking strategy (`chunk_text`), logging config, settings |
| 3 | FastAPI routers, Pydantic schemas, dependency injection |
| 4 | SQLAlchemy async DB, lifespan startup/shutdown |
| 5 | Gemini client, streaming generation, retry logic |
| 6 | JWT auth, session management, SSE streaming, rate limiting |
| 7 | Document loading, BM25 retrieval, hybrid search patterns |
| 8 | Conversational RAG, eval harness, multi-query, prod features |

---

## Quick start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env: set GEMINI_API_KEY and SECRET_KEY

# 2a. Docker (recommended)
docker-compose up --build

# 2b. Local dev
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs available at **http://localhost:8000/docs**

---

## API reference

### Auth
```
POST /auth/register    {"username": "...", "password": "..."}
POST /auth/login       form: username=...&password=...  → {"access_token": "..."}
GET  /auth/me          → current user
```

### Documents (JWT required)
```
POST /documents/ingest
  Body: {"documents": [{"id": "doc1", "filename": "policy.txt", "text": "..."}]}
  → {"job_id": "abc12345", "status": "queued"}

GET  /documents/ingest/{job_id}/status    → {status, doc_count, chunk_count}
GET  /documents/ingest/{job_id}/progress  → SSE stream of stage events
```

### Chat (JWT required)
```
POST /chat/sessions
  Body: {"title": "Support Q&A"}  → {"id": "...", "title": "..."}

POST /chat/sessions/{id}/message
  Body: {"message": "How long does shipping take?"}
  → SSE stream:
      data: {"token": "Standard "}
      data: {"token": "shipping "}
      ...
      data: {"citations": ["seed-kb"], "cache_hit": false, "done": true}

GET  /chat/sessions/{id}/history  → full persisted conversation
```

### Ops (JWT required)
```
GET /health   → {status, db, index_chunks}  (no auth — for load balancer)
GET /stats    → query metrics, cache state, ingestion jobs
GET /eval     → runs 15-question eval suite, returns PASS/BLOCK
```

---

## Eval suite

The `/eval` endpoint runs 15 questions against the live index and scores:

- **Faithfulness** — are all claims in the answer grounded in retrieved context? (LLM-as-judge)
- **Answer relevancy** — does the answer address the actual question? (reverse-question cosine)

**Baseline scores** (set in `config.py`):

| Metric | Baseline | Block threshold |
|--------|----------|-----------------|
| Faithfulness | 0.80 | < 0.80 |
| Answer relevancy | 0.30 | < 0.30 |

If either score falls below baseline, the endpoint returns HTTP 424 (Failed Dependency). Wire this into your CI pipeline:

```bash
# In CI — block deployment if eval fails
curl -sf -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/eval | python3 -c \
  "import sys,json; r=json.load(sys.stdin); sys.exit(0 if r['deployment_gate']=='PASS' else 1)"
```

---

## Running tests

```bash
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

---

## Failure modes & scaling notes

| Failure | Current behaviour | At scale |
|---------|------------------|----------|
| Gemini 429 | 30s/60s/90s backoff, 4 retries | Pre-warm cache, use paid tier |
| Large corpus | BM25 slows above ~100k chunks | Replace `Index` with Qdrant |
| Multi-worker | In-memory cache & index diverge | Redis cache + shared vector DB |
| DB load | SQLite single-writer limit | Swap `DATABASE_URL` to Postgres |
