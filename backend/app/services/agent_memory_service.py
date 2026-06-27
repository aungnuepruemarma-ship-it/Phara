import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_memory import AgentMemory


async def add_memory(
    db: AsyncSession,
    project_id: uuid.UUID,
    agent_name: str,
    content: str,
    memory_type: str = "learning",
    source_question: str = "",
    tags: list[str] | None = None,
) -> AgentMemory:
    entry = AgentMemory(
        project_id=project_id,
        agent_name=agent_name,
        memory_type=memory_type,
        content=content,
        source_question=source_question,
        tags=tags or [],
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def list_memories(
    db: AsyncSession,
    project_id: uuid.UUID,
    agent_name: str | None = None,
    limit: int = 50,
) -> list[AgentMemory]:
    stmt = select(AgentMemory).where(AgentMemory.project_id == project_id)
    if agent_name:
        stmt = stmt.where(AgentMemory.agent_name == agent_name)
    stmt = stmt.order_by(AgentMemory.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def delete_memory(db: AsyncSession, memory_id: uuid.UUID) -> bool:
    result = await db.execute(select(AgentMemory).where(AgentMemory.id == memory_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        return False
    await db.delete(entry)
    await db.commit()
    return True
