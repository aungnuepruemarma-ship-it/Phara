import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.report import ProjectReport, TrackingRunList
from app.services import report_service, tracking_service

router = APIRouter(prefix="/projects/{project_id}", tags=["reports"])


@router.get("/report", response_model=ProjectReport)
async def get_report(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await report_service.generate_report(db, project_id)


@router.get("/tracking", response_model=TrackingRunList)
async def get_tracking_runs(
    project_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
):
    runs_raw = tracking_service.get_runs(str(project_id), max_results=limit)
    from app.schemas.report import TrackingRun
    runs = [TrackingRun(**r) for r in runs_raw]
    return TrackingRunList(project_id=str(project_id), runs=runs, total=len(runs))
