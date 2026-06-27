"""
KGService — Knowledge Graph CRUD and entity extraction.

extract_and_store_from_hypothesis() is called from the LangGraph save_node
to automatically build the project knowledge graph from every workflow run.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kg import KGEntity, KGRelation


async def extract_and_store_from_hypothesis(
    db: AsyncSession,
    hypothesis,  # Hypothesis ORM object
    project_id: str,
) -> list[KGEntity]:
    """Extract entities from hypothesis text via intelligence module and persist them."""
    try:
        from intelligence.entity_extractor import extract_entities
        entities_raw = await extract_entities(
            hypothesis.hypothesis_text,
            context=hypothesis.evidence_summary or "",
        )
    except Exception:
        return []

    created: list[KGEntity] = []
    for e in entities_raw:
        entity = KGEntity(
            id=uuid.uuid4(),
            project_id=uuid.UUID(project_id),
            name=e.name[:500],
            entity_type=e.entity_type,
            domain=e.domain,
            description=e.definition_snippet[:1000] if e.definition_snippet else None,
            source_hypothesis_id=hypothesis.id,
            confidence=e.confidence,
        )
        db.add(entity)
        created.append(entity)

    if created:
        await db.commit()
        for ent in created:
            await db.refresh(ent)

    return created


async def find_related_entities(db: AsyncSession, entity_id: uuid.UUID) -> list[KGEntity]:
    """Return entities connected to the given entity via any relation."""
    result = await db.execute(
        select(KGEntity)
        .join(KGRelation, (KGRelation.subject_id == entity_id) | (KGRelation.object_id == entity_id))
        .where(KGEntity.id != entity_id)
        .distinct()
    )
    return list(result.scalars().all())


async def get_project_graph(db: AsyncSession, project_id: uuid.UUID) -> dict:
    """Return the full graph as {nodes: [...], edges: [...]} for frontend rendering."""
    entities_result = await db.execute(
        select(KGEntity).where(KGEntity.project_id == project_id)
    )
    entities = entities_result.scalars().all()

    relations_result = await db.execute(
        select(KGRelation).where(KGRelation.project_id == project_id)
    )
    relations = relations_result.scalars().all()

    nodes = [
        {
            "id": str(e.id),
            "name": e.name,
            "entity_type": e.entity_type,
            "domain": e.domain,
            "description": e.description,
            "confidence": e.confidence,
            "source_hypothesis_id": str(e.source_hypothesis_id) if e.source_hypothesis_id else None,
        }
        for e in entities
    ]
    edges = [
        {
            "id": str(r.id),
            "source": str(r.subject_id),
            "target": str(r.object_id),
            "relation_type": r.relation_type,
            "evidence_text": r.evidence_text,
            "confidence": r.confidence,
        }
        for r in relations
    ]
    return {"nodes": nodes, "edges": edges}


async def link_analogy(
    db: AsyncSession,
    entity_a_id: uuid.UUID,
    entity_b_id: uuid.UUID,
    explanation: str,
    confidence: float,
    project_id: uuid.UUID,
) -> KGRelation:
    """Create an analogous_to relation between two entities."""
    relation = KGRelation(
        id=uuid.uuid4(),
        project_id=project_id,
        subject_id=entity_a_id,
        relation_type="analogous_to",
        object_id=entity_b_id,
        evidence_text=explanation[:2000] if explanation else None,
        confidence=confidence,
    )
    db.add(relation)
    await db.commit()
    await db.refresh(relation)
    return relation


async def list_entities(db: AsyncSession, project_id: uuid.UUID) -> list[KGEntity]:
    result = await db.execute(
        select(KGEntity).where(KGEntity.project_id == project_id).order_by(KGEntity.created_at.desc())
    )
    return list(result.scalars().all())


async def list_analogies(db: AsyncSession, project_id: uuid.UUID) -> list[dict]:
    """Return entities that are connected via analogous_to relations."""
    result = await db.execute(
        select(KGRelation)
        .where(KGRelation.project_id == project_id, KGRelation.relation_type == "analogous_to")
    )
    relations = result.scalars().all()

    out = []
    for r in relations:
        subj = await db.get(KGEntity, r.subject_id)
        obj = await db.get(KGEntity, r.object_id)
        if subj and obj:
            out.append({
                "relation_id": str(r.id),
                "entity_a": {"id": str(subj.id), "name": subj.name, "domain": subj.domain},
                "entity_b": {"id": str(obj.id), "name": obj.name, "domain": obj.domain},
                "explanation": r.evidence_text,
                "confidence": r.confidence,
            })
    return out
