"""
Scoring rubric definitions for hypothesis evaluation.

Five dimensions with fixed weights summing to 1.0.
"""
from __future__ import annotations

from dataclasses import dataclass, field

DIMENSION_WEIGHTS: dict[str, float] = {
    "evidence_support": 0.30,
    "specificity":      0.25,
    "coherence":        0.20,
    "novelty":          0.15,
    "cross_domain":     0.10,
}

VERDICT_THRESHOLDS = {
    "strong":   0.70,
    "moderate": 0.45,
}


@dataclass
class ScoredDimension:
    name: str          # one of DIMENSION_WEIGHTS keys
    score: float       # 0.0 – 1.0
    reasoning: str = ""


@dataclass
class EvaluationRubric:
    dimensions: list[ScoredDimension] = field(default_factory=list)
    overall: float = 0.0
    verdict: str = "weak"   # "strong" | "moderate" | "weak"

    @classmethod
    def from_dimensions(cls, dims: list[ScoredDimension]) -> "EvaluationRubric":
        overall = sum(
            d.score * DIMENSION_WEIGHTS.get(d.name, 0.0)
            for d in dims
        )
        if overall >= VERDICT_THRESHOLDS["strong"]:
            verdict = "strong"
        elif overall >= VERDICT_THRESHOLDS["moderate"]:
            verdict = "moderate"
        else:
            verdict = "weak"
        return cls(dimensions=dims, overall=round(overall, 4), verdict=verdict)

    def to_dict(self) -> dict:
        return {
            "dimensions": [
                {"name": d.name, "score": d.score, "reasoning": d.reasoning}
                for d in self.dimensions
            ],
            "overall": self.overall,
            "verdict": self.verdict,
        }
