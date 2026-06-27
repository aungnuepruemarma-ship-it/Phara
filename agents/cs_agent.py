from agents.base_agent import AgentInput, AgentOutput
from agents.llm_agent import LLMAgent

CS_KEYWORDS = frozenset([
    "algorithm", "complexity", "graph", "tree", "sorting", "search",
    "dynamic programming", "greedy", "recursion", "hash", "cache",
    "data structure", "binary", "polynomial", "np-hard", "np-complete",
    "computability", "automata", "formal language", "compiler", "runtime",
    "parallel", "distributed", "concurrency", "database", "query",
    "cryptography", "protocol", "network", "tcp", "operating system",
])


class ComputerScienceAgent(LLMAgent):
    """Specialist agent for computer science theory and systems."""

    name = "cs_research_agent"
    description = "Specializes in algorithms, complexity theory, systems, and CS fundamentals."

    def _build_system_prompt(self, input_data: AgentInput) -> str:
        prompt = (
            "You are an expert computer science research assistant with deep knowledge of "
            "algorithms, computational complexity, systems design, and theoretical CS."
        )
        lower = input_data.question.lower()
        if any(kw in lower for kw in ("np-hard", "np-complete", "complexity", "computability")):
            prompt += (
                " Apply rigorous complexity-theoretic reasoning. "
                "Distinguish between polynomial and exponential time bounds and reference known reductions."
            )
        return prompt

    def _extra_metadata(self, input_data: AgentInput) -> dict:
        lower = input_data.question.lower()
        detected = [kw for kw in CS_KEYWORDS if kw in lower]
        return {"domain": "computer_science", "detected_topics": detected}
