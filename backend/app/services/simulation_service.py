"""
simulation_service — creates, runs, and retrieves Simulation records.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.simulation import Simulation, SimulationVariantResult
from app.schemas.simulation import SimulationRequest


async def create_and_run_simulation(
    db: AsyncSession,
    project_id: str,
    user_id: str,
    req: SimulationRequest,
) -> Simulation:
    from simulations.runner import SimulationRunner
    from simulations.types import SimulationConfig, SimulationVariant

    sim_id = uuid.uuid4()
    experiment_id_uuid = uuid.UUID(req.experiment_id) if req.experiment_id else None

    # Build config dict for JSON storage
    config_dict = {
        "simulation_type": req.simulation_type,
        "question": req.question,
        "project_id": project_id,
        "experiment_id": req.experiment_id or "",
        "user_id": user_id,
        "variants": [v.model_dump() for v in req.variants],
        "runs_per_variant": req.runs_per_variant,
    }

    sim = Simulation(
        id=sim_id,
        project_id=uuid.UUID(project_id),
        experiment_id=experiment_id_uuid,
        simulation_type=req.simulation_type,
        question=req.question,
        config=config_dict,
        status="running",
    )
    db.add(sim)
    await db.commit()
    await db.refresh(sim)

    try:
        config = SimulationConfig(
            simulation_type=req.simulation_type,
            question=req.question,
            project_id=project_id,
            experiment_id=req.experiment_id or str(sim_id),
            user_id=user_id,
            variants=[
                SimulationVariant(
                    name=v.name,
                    agent_name=v.agent_name,
                    enable_debate=v.enable_debate,
                    enable_critique=v.enable_critique,
                    enable_contradiction_check=v.enable_contradiction_check,
                    ablate_retrieval=v.ablate_retrieval,
                    ablate_memory=v.ablate_memory,
                    ablate_kg=v.ablate_kg,
                    ablate_tools=v.ablate_tools,
                    adversarial_context=list(v.adversarial_context),
                    retrieval_top_k=v.retrieval_top_k,
                )
                for v in req.variants
            ],
            runs_per_variant=req.runs_per_variant,
        )

        result = await SimulationRunner().run(config, db, str(sim_id))

        # Persist variant results (including full_state simulation memory)
        for vr in result.variant_results:
            row = SimulationVariantResult(
                simulation_id=sim_id,
                variant_name=vr.variant_name,
                agent_name=vr.agent_name,
                run_index=vr.run_index,
                hypothesis_id=uuid.UUID(vr.hypothesis_id) if vr.hypothesis_id else None,
                evaluation_score=vr.evaluation_score,
                verdict=vr.verdict,
                dimension_scores=vr.dimension_scores,
                full_state=vr.full_state or None,
            )
            db.add(row)

        sim.status = "completed"
        sim.best_variant = result.best_variant
        sim.summary = result.summary

    except Exception as exc:
        sim.status = "failed"
        sim.summary = {"error": str(exc)[:500]}

    await db.commit()

    # Return with variant_results loaded
    refreshed = await db.execute(
        select(Simulation)
        .where(Simulation.id == sim_id)
        .options(selectinload(Simulation.variant_results))
    )
    return refreshed.scalar_one()


async def get_project_simulations(db: AsyncSession, project_id: str) -> list[Simulation]:
    result = await db.execute(
        select(Simulation)
        .where(Simulation.project_id == uuid.UUID(project_id))
        .options(selectinload(Simulation.variant_results))
        .order_by(Simulation.created_at.desc())
    )
    return list(result.scalars().all())


async def get_simulation(db: AsyncSession, simulation_id: str) -> Simulation | None:
    result = await db.execute(
        select(Simulation)
        .where(Simulation.id == uuid.UUID(simulation_id))
        .options(selectinload(Simulation.variant_results))
    )
    return result.scalar_one_or_none()
