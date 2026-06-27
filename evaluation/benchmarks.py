"""
Benchmarks — three standardized quality checks run alongside the rubric scorer.

  retrieval_relevance   — keyword overlap between question and retrieved chunks
  evidence_alignment    — embedding cosine similarity between evidence and hypothesis
  contradiction_awareness — did the hypothesis address any detected contradictions?
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class BenchmarkResult:
    name: str
    score: float        # 0.0 – 1.0
    details: dict = field(default_factory=dict)


async def run_benchmarks(
    question: str,
    hypothesis_text: str,
    evidence_summary: str,
    retrieved_chunks: list[str],
    contradictions: list[dict],
) -> list[BenchmarkResult]:
    results = [
        _retrieval_relevance(question, retrieved_chunks),
        _evidence_alignment(evidence_summary, hypothesis_text),
        _contradiction_awareness(hypothesis_text, contradictions),
    ]
    return results


# ---------------------------------------------------------------------------
# Benchmark implementations
# ---------------------------------------------------------------------------

def _retrieval_relevance(question: str, chunks: list[str]) -> BenchmarkResult:
    """BM25-style keyword overlap: fraction of question keywords found in chunks."""
    if not chunks:
        return BenchmarkResult("retrieval_relevance", 0.0, {"reason": "no chunks retrieved"})

    q_tokens = set(re.findall(r'\b\w{4,}\b', question.lower()))
    if not q_tokens:
        return BenchmarkResult("retrieval_relevance", 0.5, {"reason": "no significant question tokens"})

    all_chunk_text = " ".join(chunks).lower()
    found = {t for t in q_tokens if t in all_chunk_text}
    score = round(len(found) / len(q_tokens), 3)
    return BenchmarkResult(
        "retrieval_relevance",
        score,
        {"question_tokens": len(q_tokens), "found_in_chunks": len(found)},
    )


def _evidence_alignment(evidence_summary: str, hypothesis_text: str) -> BenchmarkResult:
    """Cosine similarity between evidence and hypothesis using the project embedder."""
    if not evidence_summary or not hypothesis_text:
        return BenchmarkResult("evidence_alignment", 0.0, {"reason": "missing text"})

    try:
        from memory.embedder import embed
        import numpy as np

        vecs = embed([evidence_summary[:512], hypothesis_text[:512]])
        ev_vec = vecs[0]
        hyp_vec = vecs[1]
        norm = (np.linalg.norm(ev_vec) * np.linalg.norm(hyp_vec))
        if norm == 0:
            score = 0.0
        else:
            score = float(np.dot(ev_vec, hyp_vec) / norm)
        score = round(max(0.0, min(1.0, score)), 4)
        return BenchmarkResult("evidence_alignment", score, {"method": "cosine_embedding"})
    except Exception:
        # Fallback: word overlap
        ev_words = set(re.findall(r'\b\w{4,}\b', evidence_summary.lower()))
        hyp_words = set(re.findall(r'\b\w{4,}\b', hypothesis_text.lower()))
        if not hyp_words:
            return BenchmarkResult("evidence_alignment", 0.0, {"method": "word_overlap_fallback"})
        score = round(len(ev_words & hyp_words) / len(hyp_words), 3)
        return BenchmarkResult("evidence_alignment", score, {"method": "word_overlap_fallback"})


def _contradiction_awareness(hypothesis_text: str, contradictions: list[dict]) -> BenchmarkResult:
    """Check if hypothesis text mentions claims from detected contradictions."""
    if not contradictions:
        return BenchmarkResult(
            "contradiction_awareness", 1.0,
            {"reason": "no contradictions detected — full score awarded"},
        )

    hyp_lower = hypothesis_text.lower()
    addressed = 0
    for c in contradictions:
        claim_a = c.get("claim_a", "").lower()
        claim_b = c.get("claim_b", "").lower()
        # extract a few key words from each claim and check if hypothesis mentions them
        tokens_a = set(re.findall(r'\b\w{5,}\b', claim_a))
        tokens_b = set(re.findall(r'\b\w{5,}\b', claim_b))
        all_tokens = tokens_a | tokens_b
        if all_tokens and any(t in hyp_lower for t in all_tokens):
            addressed += 1

    score = round(addressed / len(contradictions), 3)
    return BenchmarkResult(
        "contradiction_awareness",
        score,
        {"total_contradictions": len(contradictions), "addressed": addressed},
    )
