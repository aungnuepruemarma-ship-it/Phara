import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/projects/{project_id}/knowledge-graph", tags=["knowledge-graph"])


@router.get("/graph")
async def get_graph(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    from app.services.kg_service import get_project_graph
    return await get_project_graph(db, project_id)


@router.get("/entities")
async def get_entities(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    from app.services.kg_service import list_entities
    entities = await list_entities(db, project_id)
    return [
        {
            "id": str(e.id),
            "name": e.name,
            "entity_type": e.entity_type,
            "domain": e.domain,
            "description": e.description,
            "confidence": e.confidence,
            "source_hypothesis_id": str(e.source_hypothesis_id) if e.source_hypothesis_id else None,
            "created_at": e.created_at.isoformat(),
        }
        for e in entities
    ]


@router.get("/analogies")
async def get_analogies(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    from app.services.kg_service import list_analogies
    return await list_analogies(db, project_id)
