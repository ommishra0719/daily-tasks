"""
RAG service: BM25 index + TTL cache + Gemini generation.

Composed from:
  - week-8/day-4: Index class, TTL cache, Metrics, _chunk_text
  - week-8/day-3: multi-query variant generation + dedup
  - week-8/day-1: history-aware prompt pattern
  - week-8/day-2: _gemini() helper with rate-limit backoff
"""
import asyncio
import hashlib
import json
import logging
import re
import time
from typing import AsyncGenerator, List, Tuple

from cachetools import TTLCache
from rank_bm25 import BM25Okapi

from app.config import settings

logger = logging.getLogger("rag")

# ── Gemini client ─────────────────────────────────────────────────────────────
try:
    from google import genai
    _GEMINI_AVAILABLE = bool(settings.GEMINI_API_KEY)
except ImportError:
    _GEMINI_AVAILABLE = False

_gemini_client = None


def _gemini(prompt: str, max_retries: int = 4) -> str:
    """Blocking Gemini call with per-call sleep and 429 backoff (from week-8/day-2)."""
    global _gemini_client
    if not _GEMINI_AVAILABLE:
        return "[Gemini not configured — set GEMINI_API_KEY]"
    if _gemini_client is None:
        _gemini_client = genai.Client()
    time.sleep(settings.GEMINI_CALL_DELAY)
    for attempt in range(max_retries):
        try:
            resp = _gemini_client.models.generate_content(
                model=settings.GEMINI_MODEL, contents=prompt
            )
            return resp.text.strip()
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = 30 * (attempt + 1)
                logger.warning(f"429 — waiting {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Max retries exceeded")


# ── BM25 Index (from week-8/day-4 Index class) ───────────────────────────────
class Index:
    def __init__(self):
        self.chunks: List[str] = []
        self.sources: List[str] = []        # filename per chunk for citations
        self.indexed_hashes: set = set()    # content-hash dedup
        self._bm25: BM25Okapi | None = None

    def _rebuild(self):
        if self.chunks:
            self._bm25 = BM25Okapi([c.lower().split() for c in self.chunks])

    def add(self, chunks: List[str], source: str):
        self.chunks.extend(chunks)
        self.sources.extend([source] * len(chunks))
        self._rebuild()

    def retrieve(self, query: str, k: int = 5) -> List[Tuple[str, str]]:
        """Returns list of (chunk_text, source_filename)."""
        if not self._bm25:
            return []
        scores = self._bm25.get_scores(query.lower().split())
        top_idx = sorted(range(len(self.chunks)), key=lambda i: scores[i], reverse=True)[:k]
        return [(self.chunks[i], self.sources[i]) for i in top_idx]

    @property
    def size(self) -> int:
        return len(self.chunks)


def chunk_text(text: str, size: int = None, overlap: int = None) -> List[str]:
    """Character-level chunker with overlap (from week-8/day-4)."""
    size = size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start += size - overlap
    return [c for c in chunks if c]


# ── Global singletons ─────────────────────────────────────────────────────────
index = Index()
_cache: TTLCache = TTLCache(maxsize=settings.CACHE_MAX_SIZE, ttl=settings.CACHE_TTL_SECONDS)


def _cache_key(query: str) -> str:
    return hashlib.md5(query.strip().lower().encode()).hexdigest()


# ── Metrics (from week-8/day-4) ───────────────────────────────────────────────
class Metrics:
    def __init__(self):
        self.query_count = 0
        self.cache_hits = 0
        self.latencies_ms: List[float] = []

    def record(self, ms: float, hit: bool):
        self.query_count += 1
        if hit:
            self.cache_hits += 1
        self.latencies_ms.append(ms)

    def _pct(self, p: float) -> float:
        if not self.latencies_ms:
            return 0.0
        s = sorted(self.latencies_ms)
        return round(s[min(int(len(s) * p / 100), len(s) - 1)], 2)

    def summary(self) -> dict:
        return {
            "query_count": self.query_count,
            "cache_hit_rate": round(self.cache_hits / self.query_count, 3) if self.query_count else 0.0,
            "latency_p50_ms": self._pct(50),
            "latency_p95_ms": self._pct(95),
        }


metrics = Metrics()


# ── Multi-query variant generation (from week-8/day-3) ───────────────────────
def _generate_variants(query: str, n: int = 3) -> List[str]:
    if not _GEMINI_AVAILABLE:
        return [query]  # fallback: single query
    prompt = (
        f"Rephrase the following question {n} different ways using different vocabulary. "
        "Return only the rephrased questions, one per line, no numbering.\n\nQuestion: " + query
    )
    raw = _gemini(prompt)
    return [v.strip() for v in raw.splitlines() if v.strip()][:n]


def _multi_retrieve(query: str, k: int = 5) -> List[Tuple[str, str]]:
    """Multi-query: retrieve for original + 2 variants, deduplicate by content hash."""
    variants = [query] + _generate_variants(query, n=2)
    seen, merged = set(), []
    for q in variants:
        for chunk, src in index.retrieve(q, k=k):
            h = hashlib.md5(chunk.encode()).hexdigest()
            if h not in seen:
                seen.add(h)
                merged.append((chunk, src))
    return merged[:k * 2]   # cap at 2x k


# ── RAG query (streaming) ─────────────────────────────────────────────────────
def _build_prompt(query: str, history: List[dict], context_chunks: List[Tuple[str, str]]) -> str:
    ctx = "\n\n".join(f"[{src}] {chunk}" for chunk, src in context_chunks)
    hist = ""
    if history:
        hist = "\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in history[-6:]   # last 3 turns
        )
        hist = f"\nConversation history:\n{hist}\n"
    return (
        "Answer the question using ONLY the context below. "
        "Cite sources as [filename] inline. If the context doesn't answer, say so.\n\n"
        f"Context:\n{ctx}{hist}\n\nQuestion: {query}"
    )


def rag_query(
    query: str,
    history: List[dict] | None = None,
    use_multi_query: bool = True,
) -> Tuple[str, List[str], bool]:
    """
    Returns (answer, citations, cache_hit).
    Citations are unique source filenames from retrieved chunks.
    """
    t0 = time.time()
    key = _cache_key(query)
    if key in _cache:
        cached = _cache[key]
        metrics.record((time.time() - t0) * 1000, hit=True)
        return cached["answer"], cached["citations"], True

    chunks = _multi_retrieve(query) if use_multi_query else index.retrieve(query, k=settings.RETRIEVAL_K)
    if not chunks:
        answer = "No relevant documents found in the knowledge base."
        citations: List[str] = []
    else:
        prompt = _build_prompt(query, history or [], chunks)
        answer = _gemini(prompt) if _GEMINI_AVAILABLE else chunks[0][0]
        citations = list(dict.fromkeys(src for _, src in chunks))  # unique, ordered

    _cache[key] = {"answer": answer, "citations": citations}
    metrics.record((time.time() - t0) * 1000, hit=False)
    return answer, citations, False


async def rag_query_stream(
    query: str,
    history: List[dict] | None = None,
) -> AsyncGenerator[str, None]:
    """
    SSE-ready async generator. Streams tokens as JSON events:
      {"token": "..."} — answer fragment
      {"citations": [...], "cache_hit": bool, "done": true} — final event
    """
    key = _cache_key(query)
    if key in _cache:
        cached = _cache[key]
        # Simulate streaming from cache — emit in small chunks
        answer = cached["answer"]
        for word in answer.split():
            yield json.dumps({"token": word + " "})
            await asyncio.sleep(0)
        yield json.dumps({"citations": cached["citations"], "cache_hit": True, "done": True})
        return

    # Run blocking retrieval + generation in thread pool so we don't block the event loop
    loop = asyncio.get_event_loop()
    answer, citations, cache_hit = await loop.run_in_executor(None, rag_query, query, history)

    for word in answer.split():
        yield json.dumps({"token": word + " "})
        await asyncio.sleep(0)

    yield json.dumps({"citations": citations, "cache_hit": cache_hit, "done": True})
