import uuid
from datetime import datetime

from pydantic import BaseModel


class HypothesisOut(BaseModel):
    id: uuid.UUID
    experiment_id: uuid.UUID
    question: str
    retrieved_paper_ids: list[str]
    evidence_summary: str
    hypothesis_text: str
    agent_used: str
    confidence_score: float | None
    created_at: datetime

    model_config = {"from_attributes": True}
