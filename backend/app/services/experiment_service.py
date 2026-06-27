import uuid
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.experiment import Experiment
from app.schemas.experiment import ExperimentCreate, ExperimentDetail, ExperimentUpdate


async def list_experiments(db: AsyncSession, project_id: uuid.UUID) -> Sequence[Experiment]:
    result = await db.execute(
        select(Experiment).where(Experiment.project_id == project_id).order_by(Experiment.created_at.desc())
    )
    return result.scalars().all()


async def get_experiment(db: AsyncSession, experiment_id: uuid.UUID, project_id: uuid.UUID) -> Experiment:
    result = await db.execute(
        select(Experiment)
        .options(selectinload(Experiment.hypotheses))
        .where(Experiment.id == experiment_id, Experiment.project_id == project_id)
    )
    experiment = result.scalar_one_or_none()
    if not experiment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    return experiment


async def create_experiment(db: AsyncSession, data: ExperimentCreate, project_id: uuid.UUID) -> Experiment:
    experiment = Experiment(id=uuid.uuid4(), project_id=project_id, **data.model_dump())
    db.add(experiment)
    await db.commit()
    await db.refresh(experiment)
    return experiment


async def update_experiment(
    db: AsyncSession, experiment_id: uuid.UUID, data: ExperimentUpdate, project_id: uuid.UUID
) -> Experiment:
    experiment = await get_experiment(db, experiment_id, project_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(experiment, field, value)
    await db.commit()
    await db.refresh(experiment)
    return experiment


async def delete_experiment(db: AsyncSession, experiment_id: uuid.UUID, project_id: uuid.UUID) -> None:
    experiment = await get_experiment(db, experiment_id, project_id)
    await db.delete(experiment)
    await db.commit()
