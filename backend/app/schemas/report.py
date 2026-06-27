import uuid
from datetime import datetime

from pydantic import BaseModel


class ContradictionItem(BaseModel):
    claim_a: str
    source_a: int
    claim_b: str
    source_b: int
    explanation: str
    severity: str  # "high" | "medium" | "low"


class TrackingRun(BaseModel):
    run_id: str
    start_time: str | None = None
    status: str | None = None
    params: dict = {}
    metrics: dict = {}
    tags: dict = {}


class ProjectReport(BaseModel):
    project_id: uuid.UUID
    project_name: str
    generated_at: datetime
    experiment_count: int
    hypothesis_count: int
    hypotheses: list[dict]
    synthesis: str
    top_agents: list[str]
    avg_confidence: float | None


class TrackingRunList(BaseModel):
    project_id: str
    runs: list[TrackingRun]
    total: int
