from agents.agent_registry import get_agent
from agents.base_agent import AgentInput
from workflows.base_step import BaseWorkflowStep, PipelineContext


class GenerateHypothesisStep(BaseWorkflowStep):
    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        agent = get_agent(ctx.agent_name)

        parameters: dict = {}
        tool_results = getattr(ctx, "tool_results", None) or []
        if tool_results:
            # Summarize tool outputs into a context string for the agent
            tool_context_parts = []
            for tr in tool_results:
                if not tr.get("success"):
                    continue
                name = tr.get("tool_name", "tool")
                output = tr.get("output")
                if isinstance(output, list) and output:
                    preview = str(output[:3])[:400]
                elif output:
                    preview = str(output)[:400]
                else:
                    continue
                tool_context_parts.append(f"[{name}]: {preview}")
            if tool_context_parts:
                parameters["tool_context"] = "\n".join(tool_context_parts)

        input_data = AgentInput(
            question=ctx.question,
            context=ctx.retrieved_chunks,
            parameters=parameters,
        )
        ctx.hypothesis = await agent.arun(input_data)
        return ctx
