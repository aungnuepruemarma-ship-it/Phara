import uuid

from pydantic import BaseModel

from app.schemas.hypothesis import HypothesisOut


class WorkflowRequest(BaseModel):
    question: str
    project_id: uuid.UUID
    experiment_id: uuid.UUID
    agent_name: str = "math_research_agent"


class WorkflowResult(BaseModel):
    hypothesis: HypothesisOut
    evidence_summary: str
    retrieved_paper_count: int
