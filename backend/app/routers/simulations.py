from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.routers.auth import get_current_user
from app.schemas.simulation import SimulationOut, SimulationRequest, VariantResultOut
import app.services.simulation_service as svc

router = APIRouter(tags=["simulations"])


@router.get(
    "/projects/{project_id}/simulation-knowledge",
    response_model=list[dict],
)
async def get_simulation_knowledge(
    project_id: str,
    _current_user=Depends(get_current_user),
):
    """Return simulation lessons stored in the knowledge base for this project."""
    try:
        from memory.knowledge_memory import search_knowledge
        entries = search_knowledge(
            query="simulation lessons research workflow agent performance",
            project_id=project_id,
            top_k=30,
            kind="simulation_lesson",
        )
        return [
            {
                "text": e.text,
                "source_simulation_id": e.source_paper_id,
                "score": round(e.score, 4),
            }
            for e in entries
        ]
    except Exception:
        return []


@router.post(
    "/projects/{project_id}/simulations",
    response_model=SimulationOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_simulation(
    project_id: str,
    req: SimulationRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    sim = await svc.create_and_run_simulation(db, project_id, str(current_user.id), req)
    return _to_out(sim)


@router.get(
    "/projects/{project_id}/simulations",
    response_model=list[SimulationOut],
)
async def list_simulations(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    sims = await svc.get_project_simulations(db, project_id)
    return [_to_out(s) for s in sims]


@router.get(
    "/projects/{project_id}/simulations/{simulation_id}",
    response_model=SimulationOut,
)
async def get_simulation(
    project_id: str,
    simulation_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    sim = await svc.get_simulation(db, simulation_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return _to_out(sim)


def _to_out(sim) -> SimulationOut:
    return SimulationOut(
        id=sim.id,
        project_id=sim.project_id,
        experiment_id=sim.experiment_id,
        simulation_type=sim.simulation_type,
        question=sim.question,
        status=sim.status,
        best_variant=sim.best_variant,
        summary=sim.summary,
        variant_results=[
            VariantResultOut(
                id=vr.id,
                variant_name=vr.variant_name,
                agent_name=vr.agent_name,
                run_index=vr.run_index,
                hypothesis_id=vr.hypothesis_id,
                evaluation_score=vr.evaluation_score,
                verdict=vr.verdict,
                dimension_scores=vr.dimension_scores or [],
                full_state=vr.full_state,
                created_at=vr.created_at,
            )
            for vr in (sim.variant_results or [])
        ],
        created_at=sim.created_at,
        updated_at=sim.updated_at,
    )
