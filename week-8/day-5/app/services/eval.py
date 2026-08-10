"""
Eval service — faithfulness + answer_relevancy via LLM-as-judge.
Ported from week-8/day-2/rag_eval.py; runs against the live index.
Called by GET /eval for the continuous quality gate.
"""
import re
import time
import logging
from typing import List, Tuple

from app.config import settings
from app.services.rag import _gemini, _GEMINI_AVAILABLE, index

logger = logging.getLogger("eval")

EVAL_QUESTIONS = [
    {"id": "q1",  "question": "How long does standard shipping take?"},
    {"id": "q2",  "question": "Do you ship to Europe?"},
    {"id": "q3",  "question": "What is the return window for a purchase?"},
    {"id": "q4",  "question": "Do I have to pay for return shipping?"},
    {"id": "q5",  "question": "How long until I get my refund back?"},
    {"id": "q6",  "question": "Does the warranty cover a cracked screen from a drop?"},
    {"id": "q7",  "question": "How do I file a warranty claim?"},
    {"id": "q8",  "question": "What are the password requirements for my account?"},
    {"id": "q9",  "question": "How do I turn on two-factor authentication?"},
    {"id": "q10", "question": "If I cancel my subscription mid-month, do I get a partial refund?"},
    {"id": "q11", "question": "Do you offer price matching with competitors?"},
    {"id": "q12", "question": "Is there a student discount available?"},
    {"id": "q13", "question": "Can I pay in installments with a buy-now-pay-later plan?"},
    {"id": "q14", "question": "What are your customer support hours?"},
    {"id": "q15", "question": "Will the app work on a phone from 2018?"},
]

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "do", "does", "did", "i",
    "you", "my", "your", "to", "for", "of", "in", "on", "at", "and", "or",
    "it", "this", "that", "can", "will", "be", "with", "if", "how", "what",
    "when", "get", "have", "has", "not", "also", "back", "up", "from",
}


def _kw(text: str) -> set:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOPWORDS}


def _split_claims(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def judge_faithfulness(answer: str, context: List[str]) -> Tuple[float, str]:
    claims = _split_claims(answer)
    if not claims:
        return 0.0, "no claims"
    ctx = " ".join(context)

    if _GEMINI_AVAILABLE:
        prompt = (
            "Context:\n" + ctx + "\n\nClaims:\n"
            + "\n".join(f"{i+1}. {c}" for i, c in enumerate(claims))
            + "\n\nFor each claim reply YES if supported by context else NO. One per line."
        )
        raw = _gemini(prompt)
        verdicts = [v.strip().upper() for v in raw.splitlines() if v.strip()]
        supported = sum(1 for v in verdicts if v.startswith("YES"))
        return round(supported / len(claims), 2), f"{supported}/{len(claims)}"

    # Local fallback: keyword coverage (from week-8/day-2)
    ctx_kw = _kw(ctx)
    supported = sum(1 for c in claims if len(_kw(c) & ctx_kw) / max(len(_kw(c)), 1) >= 0.6)
    return round(supported / len(claims), 2), f"{supported}/{len(claims)}"


def judge_relevancy(question: str, answer: str) -> float:
    if _GEMINI_AVAILABLE:
        prompt = (
            f"Answer: {answer}\n\n"
            "Generate 3 questions this answer could be responding to, one per line."
        )
        raw = _gemini(prompt)
        gen_qs = [q.strip() for q in raw.splitlines() if q.strip()][:3]
        q_kw = _kw(question)
        if not q_kw:
            return 0.0
        coverages = [len(q_kw & _kw(gq)) / len(q_kw) for gq in gen_qs]
        return round(sum(coverages) / len(coverages), 2)

    q_kw, a_kw = _kw(question), _kw(answer)
    return round(len(q_kw & a_kw) / len(q_kw), 2) if q_kw else 0.0


def run_eval() -> dict:
    """
    Runs all 15 eval questions against the live index.
    Returns scores + pass/fail against baseline thresholds.
    Blocks on Gemini calls — only call from a background thread or /eval endpoint.
    """
    from app.services.rag import rag_query
    results = []
    for item in EVAL_QUESTIONS:
        q = item["question"]
        answer, citations, _ = rag_query(q, use_multi_query=False)
        ctx = [chunk for chunk, _ in index.retrieve(q, k=3)]
        faith, faith_reason = judge_faithfulness(answer, ctx)
        rel = judge_relevancy(q, answer)
        logger.info(f"[{item['id']}] faith={faith} rel={rel}")
        results.append({
            "id": item["id"],
            "question": q,
            "answer": answer,
            "citations": citations,
            "faithfulness": faith,
            "faithfulness_reason": faith_reason,
            "answer_relevancy": rel,
        })

    mean_faith = round(sum(r["faithfulness"] for r in results) / len(results), 2)
    mean_rel = round(sum(r["answer_relevancy"] for r in results) / len(results), 2)

    faith_pass = mean_faith >= settings.EVAL_BASELINE_FAITHFULNESS
    rel_pass = mean_rel >= settings.EVAL_BASELINE_RELEVANCY

    return {
        "timestamp": time.time(),
        "judge": "gemini" if _GEMINI_AVAILABLE else "local_keyword_fallback",
        "mean_faithfulness": mean_faith,
        "mean_answer_relevancy": mean_rel,
        "faithfulness_pass": faith_pass,
        "relevancy_pass": rel_pass,
        "deployment_gate": "PASS" if (faith_pass and rel_pass) else "BLOCK",
        "baselines": {
            "faithfulness": settings.EVAL_BASELINE_FAITHFULNESS,
            "answer_relevancy": settings.EVAL_BASELINE_RELEVANCY,
        },
        "results": results,
    }
