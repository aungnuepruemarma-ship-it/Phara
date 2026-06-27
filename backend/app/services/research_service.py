import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.research import DebateEntry, WorkflowRequest, WorkflowResult

# Ensure repo root is importable when running inside the backend container
_repo_root = str(Path(__file__).resolve().parents[4])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


async def run_research_workflow(request: WorkflowRequest, db: AsyncSession, current_user: User) -> WorkflowResult:
    from workflows.base_step import PipelineContext
    from workflows.pipeline import ResearchPipeline
    from workflows.steps.critique_step import CritiqueStep
    from workflows.steps.debate_step import DebateStep
    from workflows.steps.generate_hypothesis import GenerateHypothesisStep
    from workflows.steps.retrieve_papers import RetrievePapersStep
    from workflows.steps.save_experiment import SaveExperimentStep
    from workflows.steps.summarize_evidence import SummarizeEvidenceStep
    from app.config import settings

    pipeline = ResearchPipeline(
        steps=[
            RetrievePapersStep(top_k=settings.retrieval_top_k),
            SummarizeEvidenceStep(),
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
    )
    ctx = await pipeline.run(ctx)

    from sqlalchemy import select
    from app.models.hypothesis import Hypothesis
    import uuid

    result = await db.execute(select(Hypothesis).where(Hypothesis.id == uuid.UUID(ctx.saved_hypothesis_id)))
    hypothesis = result.scalar_one()

    debate_entries = [
        DebateEntry(
            role=d.metadata.get("debate_role", "unknown"),
            hypothesis=d.hypothesis,
            reasoning=d.reasoning,
            confidence=d.confidence,
        )
        for d in ctx.debate_results
    ]

    critique_entry = None
    if ctx.critique is not None:
        critique_entry = DebateEntry(
            role="critic",
            hypothesis=ctx.critique.hypothesis,
            reasoning=ctx.critique.reasoning,
            confidence=ctx.critique.confidence,
        )

    return WorkflowResult(
        hypothesis=hypothesis,
        evidence_summary=ctx.evidence_summary,
        retrieved_paper_count=len(ctx.retrieved_paper_ids),
        debate=debate_entries,
        critique=critique_entry,
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
