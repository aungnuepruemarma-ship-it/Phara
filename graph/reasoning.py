"""reasoning — graph inference: find paths, analogies, and contradiction chains."""
from __future__ import annotations

from typing import Any


async def find_paths(source_id: str, target_id: str, db: Any, max_hops: int = 3) -> list[list[dict]]:
    """BFS over KGRelation edges to find paths between two entities."""
    import uuid
    from sqlalchemy import select, or_
    from app.models.kg import KGRelation

    visited: set[str] = set()
    queue: list[tuple[str, list[dict]]] = [(source_id, [])]
    paths: list[list[dict]] = []

    for _ in range(max_hops):
        if not queue:
            break
        next_queue: list[tuple[str, list[dict]]] = []
        for node_id, path in queue:
            if node_id in visited:
                continue
            visited.add(node_id)
            result = await db.execute(
                select(KGRelation).where(
                    or_(
                        KGRelation.subject_id == uuid.UUID(node_id),
                        KGRelation.object_id == uuid.UUID(node_id),
                    )
                )
            )
            for rel in result.scalars().all():
                next_id = str(rel.object_id) if str(rel.subject_id) == node_id else str(rel.subject_id)
                edge = {"relation_type": rel.relation_type, "confidence": rel.confidence}
                new_path = path + [edge]
                if next_id == target_id:
                    paths.append(new_path)
                elif next_id not in visited:
                    next_queue.append((next_id, new_path))
        queue = next_queue

    return paths


async def find_contradictions(project_id: str, db: Any) -> list[dict]:
    """Return entity pairs connected by 'contradicts' relations."""
    import uuid
    from sqlalchemy import select
    from app.models.kg import KGRelation, KGEntity

    result = await db.execute(
        select(KGRelation).where(
            KGRelation.project_id == uuid.UUID(project_id),
            KGRelation.relation_type == "contradicts",
        )
    )
    contradictions = []
    for rel in result.scalars().all():
        contradictions.append({
            "subject_id": str(rel.subject_id),
            "object_id": str(rel.object_id),
            "evidence": rel.evidence_text,
            "confidence": rel.confidence,
        })
    return contradictions
