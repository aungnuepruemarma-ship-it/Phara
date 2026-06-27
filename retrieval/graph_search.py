"""graph_search — retrieve entities and evidence from the knowledge graph."""
from __future__ import annotations

from typing import Any


async def graph_search(query: str, project_id: str, db: Any, top_k: int = 5) -> list[dict]:
    """Find KG entities whose names match the query tokens."""
    import uuid
    from sqlalchemy import select
    from app.models.kg import KGEntity

    tokens = [t.lower() for t in query.split() if len(t) > 3]
    if not tokens:
        return []

    result = await db.execute(
        select(KGEntity).where(KGEntity.project_id == uuid.UUID(project_id))
    )
    entities = result.scalars().all()

    scored = []
    for e in entities:
        name_lower = e.name.lower()
        matches = sum(1 for t in tokens if t in name_lower)
        if matches:
            scored.append({
                "text": f"{e.name}: {e.description or ''}",
                "score": matches / len(tokens),
                "entity_id": str(e.id),
                "entity_type": e.entity_type,
                "domain": e.domain,
            })

    scored.sort(key=lambda x: -x["score"])
    return scored[:top_k]
