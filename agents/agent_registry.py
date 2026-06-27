from agents.ai_research_agent import AIResearchAgent
from agents.base_agent import BaseAgent
from agents.biology_agent import BiologyAgent
from agents.critic_agent import CriticAgent
from agents.cs_agent import ComputerScienceAgent
from agents.math_research_agent import MathResearchAgent
from agents.physics_agent import PhysicsAgent
from agents.planner_agent import PlannerAgent

AGENT_REGISTRY: dict[str, type[BaseAgent]] = {
    MathResearchAgent.name: MathResearchAgent,
    AIResearchAgent.name: AIResearchAgent,
    ComputerScienceAgent.name: ComputerScienceAgent,
    PhysicsAgent.name: PhysicsAgent,
    BiologyAgent.name: BiologyAgent,
    CriticAgent.name: CriticAgent,
    PlannerAgent.name: PlannerAgent,
}


def get_agent(name: str) -> BaseAgent:
    cls = AGENT_REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown agent: {name!r}. Available: {list(AGENT_REGISTRY)}")
    return cls()


def list_agents() -> list[dict]:
    return [{"name": cls.name, "description": cls.description} for cls in AGENT_REGISTRY.values()]
