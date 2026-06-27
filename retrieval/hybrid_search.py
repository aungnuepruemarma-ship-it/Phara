"""hybrid_search — merge vector and graph retrieval results with RRF fusion."""
from __future__ import annotations

from typing import Any


async def hybrid_search(
    query: str,
    project_id: str,
    db: Any | None = None,
    top_k: int = 5,
    vector_weight: float = 0.7,
) -> list[dict]:
    """Merge vector-search and graph-search results using reciprocal rank fusion."""
    from retrieval.vector_search import vector_search as _vs

    vector_results = await _vs(query=query, project_id=project_id, top_k=top_k * 2)
    graph_results: list[dict] = []

    if db is not None:
        from retrieval.graph_search import graph_search as _gs
        graph_results = await _gs(query=query, project_id=project_id, db=db, top_k=top_k * 2)

    # Reciprocal Rank Fusion
    scores: dict[str, float] = {}
    texts: dict[str, str] = {}
    k = 60  # RRF constant

    for rank, item in enumerate(vector_results):
        key = item["text"][:100]
        scores[key] = scores.get(key, 0.0) + vector_weight / (k + rank + 1)
        texts[key] = item["text"]

    for rank, item in enumerate(graph_results):
        key = item["text"][:100]
        scores[key] = scores.get(key, 0.0) + (1 - vector_weight) / (k + rank + 1)
        texts[key] = item["text"]

    ranked = sorted(scores.items(), key=lambda x: -x[1])
    return [{"text": texts[k], "score": round(s, 4)} for k, s in ranked[:top_k]]
