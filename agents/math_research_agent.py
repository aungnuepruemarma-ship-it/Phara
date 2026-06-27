from agents.base_agent import AgentInput, AgentOutput
from agents.llm_agent import LLMAgent

MATH_KEYWORDS = frozenset([
    "theorem", "proof", "equation", "formula", "matrix", "eigenvalue",
    "integral", "gradient", "optimization", "convergence", "bound",
    "lemma", "corollary", "derivative", "divergence", "probability",
    "distribution", "entropy", "manifold", "topology",
])


class MathResearchAgent(LLMAgent):
    """Specialist agent for mathematical and quantitative research questions."""

    name = "math_research_agent"
    description = "Specializes in mathematical reasoning, theorem analysis, and quantitative hypothesis generation."

    def _build_system_prompt(self, input_data: AgentInput) -> str:
        base = "You are a rigorous research assistant generating evidence-based hypotheses."
        if self._is_math_heavy(input_data.question):
            base += (
                " Pay special attention to mathematical rigor: cite theorems, use precise notation,"
                " and distinguish proven facts from conjectures."
            )
        return base

    def _is_math_heavy(self, question: str) -> bool:
        lower = question.lower()
        return any(kw in lower for kw in MATH_KEYWORDS)

    def _extra_metadata(self, input_data: AgentInput) -> dict:
        return {"math_detected": self._is_math_heavy(input_data.question)}
