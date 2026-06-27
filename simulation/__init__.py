"""simulation — virtual scientific laboratory (Blueprint v1.0).

Re-exports from simulations/ for backward compatibility.
New code should import from simulation.*

Modules:
  runner     — orchestrates multi-variant research runs
  scheduler  — queue and prioritise simulation jobs
  variants   — SimulationVariant + SimulationConfig types
  monte_carlo     — repeated sampling runs for uncertainty estimation
  agent_sweep     — systematic comparison of different agents
  parameter_sweep — vary retrieval/model parameters
  ablation        — remove components to measure contribution
  stability       — test hypothesis reproducibility across runs
  cross_domain    — run same question across multiple domain agents
  report          — generate structured simulation reports
"""
# Backward-compat re-exports
from simulations.runner import SimulationRunner
from simulations.types import (
    SimulationConfig,
    SimulationVariant,
    VariantResult,
    SimulationResult,
)

__all__ = [
    "SimulationRunner",
    "SimulationConfig",
    "SimulationVariant",
    "VariantResult",
    "SimulationResult",
]
