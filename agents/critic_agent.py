from agents.base_agent import AgentInput, AgentOutput
from agents.llm_agent import LLMAgent


class CriticAgent(LLMAgent):
    """Critiques and stress-tests research hypotheses for logical gaps and unsupported claims."""

    name = "critic_agent"
    description = "Reviews hypotheses for logical consistency, unsupported claims, and experimental feasibility."
    temperature: float = 0.4

    def _build_system_prompt(self, input_data: AgentInput) -> str:
        return (
            "You are a rigorous scientific critic. Your role is NOT to generate a new hypothesis "
            "but to critically evaluate the provided evidence and question. "
            "Identify: (1) logical gaps or leaps of faith, (2) claims not supported by the evidence, "
            "(3) alternative explanations the evidence cannot rule out, "
            "(4) experimental or methodological weaknesses. "
            "Be constructive but precise. Assign a confidence penalty if serious flaws are found."
        )

    def _build_user_prompt(self, input_data: AgentInput) -> str:
        evidence = "\n\n".join(f"[Source {i+1}]: {chunk}" for i, chunk in enumerate(input_data.context))
        existing = input_data.parameters.get("existing_hypothesis", "")
        critique_target = f"\n\nHypothesis under review:\n{existing}" if existing else ""
        return (
            f"Evidence:\n{evidence}\n\n"
            f"Research question: {input_data.question}"
            f"{critique_target}\n\n"
            'Respond with JSON: {"hypothesis": "<critique_summary>", "reasoning": "<detailed_critique>", "confidence": 0.0-1.0}'
            "\nNote: 'hypothesis' field should contain a concise summary of your critique; "
            "'confidence' reflects your confidence in the critique (not in the original hypothesis)."
        )

    def _extra_metadata(self, input_data: AgentInput) -> dict:
        return {
            "domain": "critique",
            "has_existing_hypothesis": bool(input_data.parameters.get("existing_hypothesis")),
        }
