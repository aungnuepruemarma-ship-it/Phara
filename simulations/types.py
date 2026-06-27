"""
Simulation framework dataclasses.

SimulationConfig describes what to run.
SimulationResult captures aggregated outcomes across all variants and runs.

Sprint 6 additions:
  - Ablation flags on SimulationVariant (retrieval / memory / KG / tools)
  - adversarial_context: inject misleading chunks for adversarial simulation
  - retrieval_top_k: override retrieval depth for scaling simulation
  - full_state on VariantResult: captures complete intermediate state (simulation memory)
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
    # Ablation framework
    ablate_retrieval: bool = False      # skip paper retrieval entirely
    ablate_memory: bool = False         # disable knowledge_search tool
    ablate_kg: bool = False             # skip KG enrichment + cross-domain node
    ablate_tools: bool = False          # disable all enabled_tools
    adversarial_context: list[str] = field(default_factory=list)  # inject misleading chunks
    retrieval_top_k: int | None = None  # override top-k for scaling simulation


@dataclass
class SimulationConfig:
    simulation_type: str
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
    # Sprint 6: simulation memory — full intermediate state snapshot
    full_state: dict = field(default_factory=dict)


@dataclass
class SimulationResult:
    simulation_id: str
    config: SimulationConfig
    variant_results: list[VariantResult] = field(default_factory=list)
    best_variant: str | None = None
    summary: dict = field(default_factory=dict)
