"""
DebateStep — two specialist agents argue opposing sides of the hypothesis question.
Agent 1 defends the generated hypothesis; Agent 2 (critic) attacks it.
Results are stored in ctx.debate_results for downstream use or display.
"""
from agents.agent_registry import get_agent
from agents.base_agent import AgentInput
from workflows.base_step import BaseWorkflowStep, PipelineContext

_PRO_INSTRUCTION = (
    "You are arguing IN FAVOR of the following hypothesis. Build the strongest possible case "
    "using the evidence provided. Acknowledge limitations but ultimately defend the hypothesis."
)
_CON_INSTRUCTION = (
    "You are arguing AGAINST the following hypothesis. Identify every weakness, alternative "
    "explanation, and unsupported assumption. Be rigorous and precise."
)


class DebateStep(BaseWorkflowStep):
    """Stage a structured debate between pro-hypothesis and anti-hypothesis agents."""

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        if not ctx.enable_debate or ctx.hypothesis is None:
            return ctx

        hypothesis_text = ctx.hypothesis.hypothesis

        pro_agent = get_agent(ctx.agent_name)
        pro_input = AgentInput(
            question=ctx.question,
            context=ctx.retrieved_chunks,
            parameters={"debate_role": "pro", "hypothesis": hypothesis_text, "instruction": _PRO_INSTRUCTION},
        )

        critic_agent = get_agent("critic_agent")
        con_input = AgentInput(
            question=ctx.question,
            context=ctx.retrieved_chunks,
            parameters={"debate_role": "con", "hypothesis": hypothesis_text, "instruction": _CON_INSTRUCTION},
        )

        pro_output = await pro_agent.arun(pro_input)
        pro_output.metadata["debate_role"] = "pro"

        con_output = await critic_agent.arun(con_input)
        con_output.metadata["debate_role"] = "con"

        ctx.debate_results = [pro_output, con_output]
        return ctx
