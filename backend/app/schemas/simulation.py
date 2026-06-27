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
    # Sprint 6: ablation framework
    ablate_retrieval: bool = False
    ablate_memory: bool = False
    ablate_kg: bool = False
    ablate_tools: bool = False
    adversarial_context: list[str] = []
    retrieval_top_k: int | None = None


class SimulationRequest(BaseModel):
    simulation_type: Literal[
        # Sweep types
        "agent_sweep", "parameter_sweep", "stability_test",
        "hypothesis_sweep", "debate_simulation", "cross_domain_transfer",
        # Ablation types
        "retrieval_ablation", "memory_ablation", "kg_ablation", "tool_ablation",
        # Advanced types
        "adversarial_simulation", "time_evolution", "human_loop",
        "cost_optimization", "scaling_simulation",
    ]
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
    full_state: dict | None = None
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
