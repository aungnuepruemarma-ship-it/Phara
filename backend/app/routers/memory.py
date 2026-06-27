import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.agent_memory import AgentMemoryCreate, AgentMemoryOut
from app.services import agent_memory_service

router = APIRouter(prefix="/projects/{project_id}/memory", tags=["memory"])


@router.get("/", response_model=list[AgentMemoryOut])
async def list_memories(
    project_id: uuid.UUID,
    agent_name: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await agent_memory_service.list_memories(db, project_id, agent_name=agent_name)


@router.post("/", response_model=AgentMemoryOut, status_code=201)
async def create_memory(
    project_id: uuid.UUID,
    body: AgentMemoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await agent_memory_service.add_memory(
        db,
        project_id=project_id,
        agent_name=body.agent_name,
        content=body.content,
        memory_type=body.memory_type,
        source_question=body.source_question,
        tags=body.tags,
    )


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    project_id: uuid.UUID,
    memory_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = await agent_memory_service.delete_memory(db, memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory entry not found")
