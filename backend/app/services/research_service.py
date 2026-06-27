import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.research import DebateEntry, WorkflowRequest, WorkflowResult

_repo_root = str(Path(__file__).resolve().parents[4])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


async def run_research_workflow(request: WorkflowRequest, db: AsyncSession, current_user: User) -> WorkflowResult:
    from app.config import settings
    from sqlalchemy import select
    from app.models.hypothesis import Hypothesis
    from app.models.project import Project
    import uuid

    initial_state = {
        "question": request.question,
        "project_id": str(request.project_id),
        "experiment_id": str(request.experiment_id),
        "user_id": str(current_user.id),
        "agent_name": request.agent_name,
        "enable_critique": request.enable_critique,
        "enable_debate": request.enable_debate,
        "enable_contradiction_check": request.enable_contradiction_check,
        "retrieved_chunks": [],
        "retrieved_paper_ids": [],
        "evidence_summary": "",
        "hypothesis": None,
        "saved_hypothesis_id": None,
        "debate_results": [],
        "critique": None,
        "contradictions": [],
        "mlflow_run_id": None,
        "cross_domain_insights": [],
        "kg_entities_created": [],
    }

    # Try LangGraph first; fall back to legacy pipeline
    final_state = None
    try:
        from workflows.research_graph import research_graph
        if research_graph is not None:
            final_state = await research_graph.ainvoke(
                initial_state,
                config={
                    "configurable": {
                        "thread_id": str(request.experiment_id),
                        "db": db,
                    }
                },
            )
    except Exception:
        pass

    if final_state is None:
        # Legacy fallback
        from workflows.base_step import PipelineContext
        from workflows.pipeline import ResearchPipeline
        from workflows.steps.contradiction_step import ContradictionStep
        from workflows.steps.critique_step import CritiqueStep
        from workflows.steps.debate_step import DebateStep
        from workflows.steps.generate_hypothesis import GenerateHypothesisStep
        from workflows.steps.retrieve_papers import RetrievePapersStep
        from workflows.steps.save_experiment import SaveExperimentStep
        from workflows.steps.summarize_evidence import SummarizeEvidenceStep

        pipeline = ResearchPipeline(
            steps=[
                RetrievePapersStep(top_k=settings.retrieval_top_k),
                SummarizeEvidenceStep(),
                ContradictionStep(),
                GenerateHypothesisStep(),
                CritiqueStep(),
                DebateStep(),
                SaveExperimentStep(db=db),
            ]
        )
        ctx = PipelineContext(
            question=request.question,
            project_id=str(request.project_id),
            experiment_id=str(request.experiment_id),
            user_id=str(current_user.id),
            agent_name=request.agent_name,
            enable_critique=request.enable_critique,
            enable_debate=request.enable_debate,
            enable_contradiction_check=request.enable_contradiction_check,
        )
        ctx = await pipeline.run(ctx)
        # Convert to state dict for unified downstream handling
        final_state = {
            "saved_hypothesis_id": ctx.saved_hypothesis_id,
            "evidence_summary": ctx.evidence_summary,
            "retrieved_paper_ids": ctx.retrieved_paper_ids,
            "retrieved_chunks": ctx.retrieved_chunks,
            "contradictions": ctx.contradictions,
            "debate_results": ctx.debate_results,
            "critique": ctx.critique,
            "mlflow_run_id": ctx.mlflow_run_id,
            "enable_debate": ctx.enable_debate,
            "enable_critique": ctx.enable_critique,
            "cross_domain_insights": [],
            "kg_entities_created": [],
        }

    result = await db.execute(
        select(Hypothesis).where(Hypothesis.id == uuid.UUID(final_state["saved_hypothesis_id"]))
    )
    hypothesis = result.scalar_one()

    # Log to MLflow (best-effort)
    try:
        from tracking.mlflow_tracker import RunMetrics, RunParams, log_research_run
        proj_result = await db.execute(select(Project).where(Project.id == request.project_id))
        project = proj_result.scalar_one_or_none()
        run_id = log_research_run(
            params=RunParams(
                question=request.question,
                agent_name=request.agent_name,
                project_id=str(request.project_id),
                experiment_id=str(request.experiment_id),
            ),
            metrics=RunMetrics(
                confidence_score=hypothesis.confidence_score or 0.0,
                retrieved_paper_count=len(final_state.get("retrieved_paper_ids", [])),
                chunk_count=len(final_state.get("retrieved_chunks", [])),
                contradiction_count=len(final_state.get("contradictions", [])),
                debate_enabled=final_state.get("enable_debate", False),
                critique_enabled=final_state.get("enable_critique", False),
            ),
            hypothesis_text=hypothesis.hypothesis_text,
            evidence_summary=final_state.get("evidence_summary", ""),
            project_name=project.name if project else "",
        )
        if not final_state.get("mlflow_run_id"):
            final_state["mlflow_run_id"] = run_id
    except Exception:
        pass

    debate_results = final_state.get("debate_results") or []
    debate_entries = [
        DebateEntry(
            role=d.metadata.get("debate_role", "unknown"),
            hypothesis=d.hypothesis,
            reasoning=d.reasoning,
            confidence=d.confidence,
        )
        for d in debate_results
    ]

    critique_raw = final_state.get("critique")
    critique_entry = None
    if critique_raw is not None:
        critique_entry = DebateEntry(
            role="critic",
            hypothesis=critique_raw.hypothesis,
            reasoning=critique_raw.reasoning,
            confidence=critique_raw.confidence,
        )

    return WorkflowResult(
        hypothesis=hypothesis,
        evidence_summary=final_state.get("evidence_summary", ""),
        retrieved_paper_count=len(final_state.get("retrieved_paper_ids", [])),
        debate=debate_entries,
        critique=critique_entry,
        contradictions=final_state.get("contradictions", []),
        mlflow_run_id=final_state.get("mlflow_run_id"),
    )


async def list_history(db: AsyncSession, current_user: User):
    from sqlalchemy import select
    from app.models.hypothesis import Hypothesis
    from app.models.experiment import Experiment
    from app.models.project import Project

    result = await db.execute(
        select(Hypothesis)
        .join(Experiment, Hypothesis.experiment_id == Experiment.id)
        .join(Project, Experiment.project_id == Project.id)
        .where(Project.owner_id == current_user.id)
        .order_by(Hypothesis.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()
