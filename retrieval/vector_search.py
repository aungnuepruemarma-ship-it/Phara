"""vector_search — semantic search over the project's paper and knowledge collections."""
from __future__ import annotations


async def vector_search(query: str, project_id: str, top_k: int = 5) -> list[dict]:
    """Search the vector store and return scored passages."""
    try:
        from memory.vector_store import search_chunks
        chunks = await search_chunks(query=query, project_id=project_id, top_k=top_k)
        return [{"text": c.text, "score": c.score, "source": c.paper_id} for c in chunks]
    except Exception:
        return []
