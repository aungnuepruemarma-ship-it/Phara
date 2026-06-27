import uuid

from pydantic import BaseModel

from app.schemas.hypothesis import HypothesisOut


class WorkflowRequest(BaseModel):
    question: str
    project_id: uuid.UUID
    experiment_id: uuid.UUID
    agent_name: str = "math_research_agent"
    enable_debate: bool = False
    enable_critique: bool = False


class DebateEntry(BaseModel):
    role: str
    hypothesis: str
    reasoning: str
    confidence: float


class WorkflowResult(BaseModel):
    hypothesis: HypothesisOut
    evidence_summary: str
    retrieved_paper_count: int
    debate: list[DebateEntry] = []
    critique: DebateEntry | None = None
