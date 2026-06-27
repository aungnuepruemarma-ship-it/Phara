"""
Simulation framework dataclasses.

SimulationConfig describes what to run.
SimulationResult captures aggregated outcomes across all variants and runs.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SimulationVariant:
    name: str
    agent_name: str
    enable_debate: bool = False
    enable_critique: bool = False
    enable_contradiction_check: bool = False


@dataclass
class SimulationConfig:
    simulation_type: str          # "agent_sweep" | "parameter_sweep" | "stability_test"
    question: str
    project_id: str
    experiment_id: str
    user_id: str
    variants: list[SimulationVariant] = field(default_factory=list)
    runs_per_variant: int = 1


@dataclass
class VariantResult:
    variant_name: str
    agent_name: str
    run_index: int
    hypothesis_id: str | None = None
    evaluation_score: float | None = None
    verdict: str | None = None
    dimension_scores: list[dict] = field(default_factory=list)


@dataclass
class SimulationResult:
    simulation_id: str
    config: SimulationConfig
    variant_results: list[VariantResult] = field(default_factory=list)
    best_variant: str | None = None
    summary: dict = field(default_factory=dict)
