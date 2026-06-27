from agents.base_agent import AgentInput, AgentOutput
from agents.llm_agent import LLMAgent


class PlannerAgent(LLMAgent):
    """Generates structured multi-step research plans from a question and evidence."""

    name = "planner_agent"
    description = "Creates structured research roadmaps: experiments to run, data to collect, analyses to perform."
    temperature: float = 0.5

    def _build_system_prompt(self, input_data: AgentInput) -> str:
        return (
            "You are a research planning assistant. Given a research question and relevant evidence, "
            "produce a structured investigation plan. The plan should include: "
            "(1) a falsifiable hypothesis derived from the evidence, "
            "(2) 3-5 concrete experiments or analyses to test it, "
            "(3) expected outcomes and failure modes, "
            "(4) resource and time estimates if possible. "
            "Be specific and actionable."
        )

    def _build_user_prompt(self, input_data: AgentInput) -> str:
        evidence = "\n\n".join(f"[Source {i+1}]: {chunk}" for i, chunk in enumerate(input_data.context))
        goal = input_data.parameters.get("goal", "")
        goal_str = f"\nResearch goal: {goal}" if goal else ""
        return (
            f"Evidence:\n{evidence}\n\n"
            f"Research question: {input_data.question}"
            f"{goal_str}\n\n"
            'Respond with JSON: {"hypothesis": "<central_hypothesis>", "reasoning": "<research_plan>", "confidence": 0.0-1.0}'
            "\nNote: 'reasoning' should contain the full structured research plan as markdown."
        )

    def _extra_metadata(self, input_data: AgentInput) -> dict:
        return {
            "domain": "planning",
            "goal": input_data.parameters.get("goal", ""),
        }
