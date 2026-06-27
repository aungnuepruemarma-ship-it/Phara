from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_user
from app.schemas.evaluation import EvaluationOut, EvaluationSummary
import app.services.evaluation_service as svc

router = APIRouter(tags=["evaluation"])


@router.post(
    "/projects/{project_id}/hypotheses/{hypothesis_id}/evaluate",
    response_model=EvaluationOut,
    status_code=status.HTTP_201_CREATED,
)
async def evaluate_hypothesis(
    project_id: str,
    hypothesis_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    result = await svc.evaluate_hypothesis(db, hypothesis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    return _to_out(result)


@router.get(
    "/projects/{project_id}/evaluations",
    response_model=list[EvaluationOut],
)
async def list_evaluations(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    evals = await svc.get_project_evaluations(db, project_id)
    return [_to_out(e) for e in evals]


@router.get(
    "/projects/{project_id}/evaluations/summary",
    response_model=EvaluationSummary,
)
async def evaluation_summary(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    return await svc.get_evaluation_summary(db, project_id)


def _to_out(ev) -> dict:
    from app.schemas.evaluation import DimensionScore, BenchmarkScore
    return EvaluationOut(
        id=ev.id,
        hypothesis_id=ev.hypothesis_id,
        project_id=ev.project_id,
        overall_score=ev.overall_score,
        verdict=ev.verdict,
        dimension_scores=[DimensionScore(**d) for d in (ev.dimension_scores or [])],
        benchmark_scores=[BenchmarkScore(**b) for b in (ev.benchmark_scores or [])],
        created_at=ev.created_at,
    )
