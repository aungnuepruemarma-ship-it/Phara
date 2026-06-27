"""retriever — high-level retrieval interface used by workflow nodes and tools."""
from __future__ import annotations

from typing import Any


async def retrieve(
    query: str,
    project_id: str,
    top_k: int = 5,
    db: Any | None = None,
    mode: str = "hybrid",  # "vector" | "graph" | "hybrid"
) -> list[str]:
    """Return plain text passages for the given query.

    mode:
      vector  — semantic search only
      graph   — KG entity search only (requires db)
      hybrid  — merge both (default; falls back to vector when db unavailable)
    """
    if mode == "vector":
        from retrieval.vector_search import vector_search
        results = await vector_search(query=query, project_id=project_id, top_k=top_k)
    elif mode == "graph" and db is not None:
        from retrieval.graph_search import graph_search
        results = await graph_search(query=query, project_id=project_id, db=db, top_k=top_k)
    else:
        from retrieval.hybrid_search import hybrid_search
        results = await hybrid_search(query=query, project_id=project_id, db=db, top_k=top_k)

    return [r["text"] for r in results]
