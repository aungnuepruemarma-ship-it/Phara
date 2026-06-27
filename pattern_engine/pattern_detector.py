"""pattern_detector — find recurring conceptual structures across hypotheses."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DetectedPattern:
    pattern_type: str          # optimization | feedback | compression | hierarchy | adaptation
    description: str
    domains_seen: list[str]
    frequency: int
    example_texts: list[str] = field(default_factory=list)
    confidence: float = 0.5


async def detect_patterns(hypotheses: list[str], project_id: str) -> list[DetectedPattern]:
    """Detect recurring conceptual patterns across a list of hypothesis texts.

    Uses the intelligence.pattern_miner implementation when available,
    falling back to keyword-frequency heuristics.
    """
    try:
        from intelligence.pattern_miner import mine_patterns
        return await mine_patterns(hypotheses=hypotheses, project_id=project_id)
    except Exception:
        return _heuristic_patterns(hypotheses)


def _heuristic_patterns(hypotheses: list[str]) -> list[DetectedPattern]:
    """Keyword-frequency fallback when LLM is unavailable."""
    PATTERN_KEYWORDS: dict[str, list[str]] = {
        "optimization":  ["minimize", "maximize", "optimal", "gradient", "converge"],
        "feedback":      ["feedback", "loop", "regulate", "homeostasis", "reinforcement"],
        "compression":   ["compress", "encode", "represent", "dimensionality", "latent"],
        "hierarchy":     ["hierarchy", "layer", "level", "nested", "recursive"],
        "adaptation":    ["adapt", "evolve", "learn", "update", "generalize"],
        "uncertainty":   ["uncertain", "probabilistic", "stochastic", "noise", "variance"],
    }
    counts: dict[str, int] = {k: 0 for k in PATTERN_KEYWORDS}
    for h in hypotheses:
        hl = h.lower()
        for pattern, kws in PATTERN_KEYWORDS.items():
            if any(kw in hl for kw in kws):
                counts[pattern] += 1

    results = []
    for pattern, count in counts.items():
        if count > 0:
            results.append(DetectedPattern(
                pattern_type=pattern,
                description=f"Recurring {pattern} structure detected across {count} hypotheses",
                domains_seen=[],
                frequency=count,
                confidence=min(0.4 + count * 0.1, 0.9),
            ))
    return sorted(results, key=lambda p: -p.frequency)
