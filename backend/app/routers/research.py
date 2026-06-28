from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.hypothesis import HypothesisOut
from app.schemas.research import (
    RoundtableRequest,
    RoundtableResult,
    WorkflowRequest,
    WorkflowResult,
)
from app.services import collaboration_service, research_service

router = APIRouter(prefix="/research", tags=["research"])


@router.post("/run", response_model=WorkflowResult)
async def run_workflow(
    body: WorkflowRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await research_service.run_research_workflow(body, db, current_user)


@router.post("/roundtable", response_model=RoundtableResult)
async def run_roundtable(
    body: RoundtableRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await collaboration_service.run_roundtable(body, db, current_user)


@router.get("/history", response_model=list[HypothesisOut])
async def get_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await research_service.list_history(db, current_user)


@router.get("/agents")
async def list_agents(current_user: User = Depends(get_current_user)):
    import sys
    from pathlib import Path
    _root = str(Path(__file__).resolve().parents[4])
    if _root not in sys.path:
        sys.path.insert(0, _root)
    from agents.agent_registry import list_agents as _list
    return _list()
