from agents.base_agent import BaseAgent
from agents.math_research_agent import MathResearchAgent

AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    MathResearchAgent.name: MathResearchAgent,
}


def get_agent(name: str) -> BaseAgent:
    cls = AGENT_REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown agent: {name!r}. Available: {list(AGENT_REGISTRY)}")
    return cls()


def list_agents() -> list[dict]:
    return [{"name": cls.name, "description": cls.description} for cls in AGENT_REGISTRY.values()]
