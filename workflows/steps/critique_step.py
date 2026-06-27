from agents.agent_registry import get_agent
from agents.base_agent import AgentInput
from workflows.base_step import BaseWorkflowStep, PipelineContext


class CritiqueStep(BaseWorkflowStep):
    """Have the CriticAgent review the generated hypothesis and attach critique to context."""

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        if not ctx.enable_critique or ctx.hypothesis is None:
            return ctx

        critic = get_agent("critic_agent")
        input_data = AgentInput(
            question=ctx.question,
            context=ctx.retrieved_chunks,
            parameters={"existing_hypothesis": ctx.hypothesis.hypothesis},
        )
        ctx.critique = await critic.arun(input_data)
        return ctx
