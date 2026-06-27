from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DimensionScore(BaseModel):
    name: str
    score: float
    reasoning: str = ""


class BenchmarkScore(BaseModel):
    name: str
    score: float
    details: dict = {}


class EvaluationOut(BaseModel):
    id: UUID
    hypothesis_id: UUID
    project_id: UUID
    overall_score: float
    verdict: str
    dimension_scores: list[DimensionScore]
    benchmark_scores: list[BenchmarkScore]
    created_at: datetime

    model_config = {"from_attributes": True}


class EvaluationSummary(BaseModel):
    project_id: UUID
    hypothesis_count: int
    avg_score: float | None
    best_agent: str | None
    score_trend: list[float]
