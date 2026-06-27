"""graph_store — thin wrapper over backend KG service for use outside FastAPI."""
from __future__ import annotations

from typing import Any


async def get_graph(project_id: str, db: Any) -> dict:
    """Return {nodes, edges} for a project."""
    from app.services.kg_service import get_project_graph
    return await get_project_graph(db, project_id)


async def store_entity(entity_data: dict, project_id: str, db: Any) -> Any:
    """Persist a KGEntity from a plain dict."""
    from app.models.kg import KGEntity
    import uuid as _uuid
    import sys
    from pathlib import Path
    _root = str(Path(__file__).resolve().parents[1] / "backend")
    if _root not in sys.path:
        sys.path.insert(0, _root)

    entity = KGEntity(
        project_id=_uuid.UUID(project_id),
        name=entity_data["name"],
        entity_type=entity_data.get("entity_type", "concept"),
        domain=entity_data.get("domain", "general"),
        description=entity_data.get("description"),
        confidence=float(entity_data.get("confidence", 0.8)),
    )
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return entity


async def store_relation(relation_data: dict, db: Any) -> Any:
    """Persist a KGRelation from a plain dict."""
    from app.models.kg import KGRelation
    import uuid as _uuid

    rel = KGRelation(
        project_id=_uuid.UUID(relation_data["project_id"]),
        subject_id=_uuid.UUID(relation_data["subject_id"]),
        object_id=_uuid.UUID(relation_data["object_id"]),
        relation_type=relation_data["relation_type"],
        evidence_text=relation_data.get("evidence_text"),
        confidence=float(relation_data.get("confidence", 0.8)),
    )
    db.add(rel)
    await db.commit()
    await db.refresh(rel)
    return rel
