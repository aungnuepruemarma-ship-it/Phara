"""entity_linker — deduplicate entities by matching new names to existing nodes."""
from __future__ import annotations

from typing import Any


async def find_or_create(name: str, entity_type: str, domain: str, project_id: str, db: Any) -> Any:
    """Return existing entity with same name (case-insensitive) or create a new one."""
    import uuid
    from sqlalchemy import select, func
    from app.models.kg import KGEntity

    result = await db.execute(
        select(KGEntity).where(
            KGEntity.project_id == uuid.UUID(project_id),
            func.lower(KGEntity.name) == name.lower(),
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    from graph.graph_store import store_entity
    return await store_entity(
        {"name": name, "entity_type": entity_type, "domain": domain},
        project_id=project_id,
        db=db,
    )
