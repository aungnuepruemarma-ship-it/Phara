from agents.base_agent import AgentInput, AgentOutput
from agents.llm_agent import LLMAgent

AI_KEYWORDS = frozenset([
    "neural", "network", "transformer", "attention", "training", "model",
    "loss", "backpropagation", "gradient", "optimizer", "overfitting",
    "generalization", "representation", "embedding", "fine-tuning",
    "pre-training", "reinforcement", "supervised", "unsupervised",
    "classification", "regression", "diffusion", "autoencoder", "gan",
    "llm", "language model", "vision", "multimodal", "scaling", "emergent",
])


class AIResearchAgent(LLMAgent):
    """Specialist agent for AI/ML research questions."""

    name = "ai_research_agent"
    description = "Specializes in machine learning, deep learning, and AI systems research."

    def _build_system_prompt(self, input_data: AgentInput) -> str:
        prompt = (
            "You are an expert AI/ML research assistant. "
            "You have deep knowledge of neural architectures, training dynamics, "
            "and the current state of the art in machine learning."
        )
        question_lower = input_data.question.lower()
        if any(kw in question_lower for kw in ("llm", "language model", "transformer", "attention")):
            prompt += (
                " Pay special attention to transformer architectures, attention mechanisms, "
                "and emergent capabilities at scale."
            )
        return prompt

    def _extra_metadata(self, input_data: AgentInput) -> dict:
        lower = input_data.question.lower()
        detected = [kw for kw in AI_KEYWORDS if kw in lower]
        return {"domain": "ai_ml", "detected_topics": detected}
