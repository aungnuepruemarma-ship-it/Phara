from agents.agent_registry import get_agent
from agents.base_agent import AgentInput
from workflows.base_step import BaseWorkflowStep, PipelineContext


class GenerateHypothesisStep(BaseWorkflowStep):
    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        agent = get_agent(ctx.agent_name)
        input_data = AgentInput(question=ctx.question, context=ctx.retrieved_chunks)
        ctx.hypothesis = await agent.arun(input_data)
        return ctx
