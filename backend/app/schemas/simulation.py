from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SimulationVariantIn(BaseModel):
    name: str
    agent_name: str
    enable_debate: bool = False
    enable_critique: bool = False
    enable_contradiction_check: bool = False


class SimulationRequest(BaseModel):
    simulation_type: Literal["agent_sweep", "parameter_sweep", "stability_test"]
    question: str
    experiment_id: str | None = None
    variants: list[SimulationVariantIn] = Field(min_length=1)
    runs_per_variant: int = Field(default=1, ge=1, le=10)


class VariantResultOut(BaseModel):
    id: UUID
    variant_name: str
    agent_name: str
    run_index: int
    hypothesis_id: UUID | None
    evaluation_score: float | None
    verdict: str | None
    dimension_scores: list[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


class SimulationOut(BaseModel):
    id: UUID
    project_id: UUID
    experiment_id: UUID | None
    simulation_type: str
    question: str
    status: str
    best_variant: str | None
    summary: dict | None
    variant_results: list[VariantResultOut]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
