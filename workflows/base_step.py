from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from agents.base_agent import AgentOutput


@dataclass
class PipelineContext:
    question: str
    project_id: str
    experiment_id: str
    user_id: str
    agent_name: str = "math_research_agent"
    retrieved_chunks: list[str] = field(default_factory=list)
    retrieved_paper_ids: list[str] = field(default_factory=list)
    evidence_summary: str = ""
    hypothesis: AgentOutput | None = None
    saved_hypothesis_id: str | None = None
    # Phase 4: debate and critique
    debate_results: list[AgentOutput] = field(default_factory=list)
    critique: AgentOutput | None = None
    enable_debate: bool = False
    enable_critique: bool = False
    # Phase 5: contradiction detection
    contradictions: list[dict] = field(default_factory=list)
    enable_contradiction_check: bool = False
    # MLflow run id (set after logging)
    mlflow_run_id: str | None = None


class BaseWorkflowStep(ABC):
    @abstractmethod
    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        ...
