import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ReviewStatus = Literal["candidate", "under_review", "accepted", "rejected"]


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
    review_status: ReviewStatus = "candidate"
    review_notes: str | None = None
    reviewed_at: datetime | None = None

    model_config = {"from_attributes": True}


class HypothesisReviewRequest(BaseModel):
    decision: ReviewStatus  # "accepted" | "rejected"
    notes: str | None = None
