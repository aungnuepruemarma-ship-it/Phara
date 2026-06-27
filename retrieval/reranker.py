"""reranker — cross-encoder re-scoring of candidate passages.

Uses embedding dot-product as a lightweight reranker when a full
cross-encoder model is not available.
"""
from __future__ import annotations


def rerank(query: str, passages: list[str], top_k: int = 5) -> list[tuple[str, float]]:
    """Return passages re-ranked by query-passage relevance.

    Falls back to BM25-style term overlap when embedder unavailable.
    """
    try:
        from memory.embedder import embed
        q_vec = embed(query)
        scored = []
        for p in passages:
            p_vec = embed(p)
            sim = _cosine(q_vec, p_vec)
            scored.append((p, sim))
        scored.sort(key=lambda x: -x[1])
        return scored[:top_k]
    except Exception:
        return _bm25_rerank(query, passages, top_k)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    ma = sum(x ** 2 for x in a) ** 0.5
    mb = sum(x ** 2 for x in b) ** 0.5
    return dot / (ma * mb) if ma and mb else 0.0


def _bm25_rerank(query: str, passages: list[str], top_k: int) -> list[tuple[str, float]]:
    q_tokens = set(query.lower().split())
    scored = [(p, len(q_tokens & set(p.lower().split())) / max(len(q_tokens), 1)) for p in passages]
    scored.sort(key=lambda x: -x[1])
    return scored[:top_k]
