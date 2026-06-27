import uuid
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experiment import Experiment
from app.models.note import Note
from app.models.paper import Paper
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectSummary, ProjectUpdate


async def list_projects(db: AsyncSession, owner_id: uuid.UUID) -> Sequence[Project]:
    result = await db.execute(select(Project).where(Project.owner_id == owner_id).order_by(Project.created_at.desc()))
    return result.scalars().all()


async def get_project(db: AsyncSession, project_id: uuid.UUID, owner_id: uuid.UUID) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == owner_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


async def create_project(db: AsyncSession, data: ProjectCreate, owner_id: uuid.UUID) -> Project:
    project = Project(id=uuid.uuid4(), owner_id=owner_id, **data.model_dump())
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def update_project(db: AsyncSession, project_id: uuid.UUID, data: ProjectUpdate, owner_id: uuid.UUID) -> Project:
    project = await get_project(db, project_id, owner_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project_id: uuid.UUID, owner_id: uuid.UUID) -> None:
    project = await get_project(db, project_id, owner_id)
    await db.delete(project)
    await db.commit()


async def get_project_summary(db: AsyncSession, project_id: uuid.UUID, owner_id: uuid.UUID) -> ProjectSummary:
    project = await get_project(db, project_id, owner_id)

    paper_count = (await db.execute(select(func.count()).where(Paper.project_id == project_id))).scalar()
    experiment_count = (await db.execute(select(func.count()).where(Experiment.project_id == project_id))).scalar()
    note_count = (await db.execute(select(func.count()).where(Note.project_id == project_id))).scalar()

    return ProjectSummary(
        project=project,
        paper_count=paper_count,
        experiment_count=experiment_count,
        note_count=note_count,
    )
