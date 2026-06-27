from agents.base_agent import AgentInput, AgentOutput
from agents.llm_agent import LLMAgent

PHYSICS_KEYWORDS = frozenset([
    "quantum", "classical", "mechanics", "thermodynamics", "entropy",
    "energy", "force", "field", "wave", "particle", "relativity",
    "spacetime", "gravity", "electromagnetism", "photon", "electron",
    "spin", "superposition", "entanglement", "hamiltonian", "lagrangian",
    "symmetry", "conservation", "phase transition", "condensed matter",
    "nuclear", "plasma", "optics", "fluid", "turbulence",
])


class PhysicsAgent(LLMAgent):
    """Specialist agent for physics research questions."""

    name = "physics_research_agent"
    description = "Specializes in theoretical and experimental physics, from quantum to classical mechanics."

    def _build_system_prompt(self, input_data: AgentInput) -> str:
        prompt = (
            "You are an expert physics research assistant with mastery of both theoretical "
            "and experimental physics across quantum, classical, and relativistic regimes."
        )
        lower = input_data.question.lower()
        if any(kw in lower for kw in ("quantum", "superposition", "entanglement", "spin")):
            prompt += (
                " Apply quantum mechanical formalism precisely. "
                "Reference relevant Hamiltonians, operators, and measurement postulates."
            )
        elif any(kw in lower for kw in ("relativity", "spacetime", "gravity")):
            prompt += " Apply relativistic reasoning, citing metric tensors and spacetime geometry where relevant."
        return prompt

    def _extra_metadata(self, input_data: AgentInput) -> dict:
        lower = input_data.question.lower()
        detected = [kw for kw in PHYSICS_KEYWORDS if kw in lower]
        return {"domain": "physics", "detected_topics": detected}
