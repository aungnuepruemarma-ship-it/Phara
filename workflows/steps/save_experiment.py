import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from workflows.base_step import BaseWorkflowStep, PipelineContext


class SaveExperimentStep(BaseWorkflowStep):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        from app.models.experiment import Experiment
        from app.models.hypothesis import Hypothesis

        hypothesis = Hypothesis(
            id=uuid.uuid4(),
            experiment_id=uuid.UUID(ctx.experiment_id),
            question=ctx.question,
            retrieved_paper_ids=ctx.retrieved_paper_ids,
            evidence_summary=ctx.evidence_summary,
            hypothesis_text=ctx.hypothesis.hypothesis if ctx.hypothesis else "",
            agent_used=ctx.agent_name,
            confidence_score=ctx.hypothesis.confidence if ctx.hypothesis else None,
        )
        self.db.add(hypothesis)

        from sqlalchemy import update
        await self.db.execute(
            update(Experiment)
            .where(Experiment.id == uuid.UUID(ctx.experiment_id))
            .values(status="completed")
        )
        await self.db.commit()
        await self.db.refresh(hypothesis)
        ctx.saved_hypothesis_id = str(hypothesis.id)
        return ctx
