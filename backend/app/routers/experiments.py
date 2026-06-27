import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.experiment import ExperimentCreate, ExperimentDetail, ExperimentOut, ExperimentUpdate
from app.services import experiment_service

router = APIRouter(prefix="/projects/{project_id}/experiments", tags=["experiments"])


@router.get("", response_model=list[ExperimentOut])
async def list_experiments(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await experiment_service.list_experiments(db, project_id)


@router.post("", response_model=ExperimentOut, status_code=status.HTTP_201_CREATED)
async def create_experiment(
    project_id: uuid.UUID,
    body: ExperimentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await experiment_service.create_experiment(db, body, project_id)


@router.get("/{experiment_id}", response_model=ExperimentDetail)
async def get_experiment(
    project_id: uuid.UUID,
    experiment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await experiment_service.get_experiment(db, experiment_id, project_id)


@router.put("/{experiment_id}", response_model=ExperimentOut)
async def update_experiment(
    project_id: uuid.UUID,
    experiment_id: uuid.UUID,
    body: ExperimentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await experiment_service.update_experiment(db, experiment_id, body, project_id)


@router.delete("/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experiment(
    project_id: uuid.UUID,
    experiment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await experiment_service.delete_experiment(db, experiment_id, project_id)
