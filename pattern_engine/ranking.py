"""ranking — rank candidate patterns and hypotheses by evidence strength."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RankedCandidate:
    text: str
    score: float
    rank: int
    reason: str


def rank_patterns(patterns: list[dict], evidence_weight: float = 0.6) -> list[RankedCandidate]:
    """Sort pattern dicts by a combined confidence × frequency score."""
    scored = []
    for i, p in enumerate(patterns):
        confidence = float(p.get("confidence", 0.5))
        frequency = int(p.get("frequency", 1))
        score = round(confidence * evidence_weight + min(frequency / 10.0, 1.0) * (1 - evidence_weight), 4)
        scored.append(RankedCandidate(
            text=p.get("description", str(p)),
            score=score,
            rank=0,
            reason=f"confidence={confidence:.2f}, frequency={frequency}",
        ))
    scored.sort(key=lambda c: -c.score)
    for i, c in enumerate(scored):
        c.rank = i + 1
    return scored


def rank_hypotheses(hypotheses: list[dict]) -> list[RankedCandidate]:
    """Rank hypothesis dicts by evaluation score or confidence."""
    scored = []
    for h in hypotheses:
        score = float(h.get("evaluation_score") or h.get("confidence_score") or 0.0)
        scored.append(RankedCandidate(
            text=h.get("hypothesis_text", ""),
            score=score,
            rank=0,
            reason=f"score={score:.2f}, agent={h.get('agent_used', '')}",
        ))
    scored.sort(key=lambda c: -c.score)
    for i, c in enumerate(scored):
        c.rank = i + 1
    return scored
