"""
PatternMiner — discovers recurring structural patterns across hypotheses in a project.

Targets universal patterns like: optimization, feedback loops, compression,
hierarchical organization, adaptation, uncertainty reduction, self-organization.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field


try:
    from app.config import settings as _settings
except ImportError:
    _settings = None

_SYSTEM = (
    "You are a cross-domain pattern analyst. "
    "Given a set of research hypotheses from different domains, identify recurring "
    "structural patterns that appear across multiple hypotheses. "
    "Focus on deep structural similarities, not surface keyword matches. "
    "Universal patterns include: optimization, feedback_loops, compression, "
    "hierarchical_organization, adaptation, uncertainty_reduction, "
    "self_organization, constraint_solving, phase_transitions, emergent_complexity."
)


@dataclass
class DomainPattern:
    pattern_type: str
    description: str
    domains_seen: list[str] = field(default_factory=list)
    example_hypotheses: list[str] = field(default_factory=list)
    frequency: int = 1
    confidence: float = 0.7


def _parse(text: str) -> list[DomainPattern]:
    start = text.find("[")
    end = text.rfind("]") + 1
    if start < 0 or end <= start:
        return []
    try:
        items = json.loads(text[start:end])
    except json.JSONDecodeError:
        return []
    patterns = []
    for item in items:
        if not isinstance(item, dict):
            continue
        patterns.append(DomainPattern(
            pattern_type=item.get("pattern_type", "unknown"),
            description=item.get("description", ""),
            domains_seen=item.get("domains_seen", []),
            example_hypotheses=item.get("example_hypotheses", []),
            frequency=int(item.get("frequency", 1)),
            confidence=float(item.get("confidence", 0.7)),
        ))
    return patterns


async def mine_patterns(hypothesis_texts: list[str]) -> list[DomainPattern]:
    """Find cross-domain structural patterns in a set of hypothesis texts."""
    if len(hypothesis_texts) < 2:
        return []

    from agents.llm_client import acall_llm

    items = "\n".join(f"[{i+1}] {h[:300]}" for i, h in enumerate(hypothesis_texts[:20]))
    user_prompt = (
        f"Hypotheses:\n{items}\n\n"
        "Identify recurring structural patterns across these hypotheses. "
        "Respond with a JSON array:\n"
        '[{"pattern_type": "...", "description": "...", "domains_seen": ["math", "biology", ...], '
        '"example_hypotheses": ["...", "..."], "frequency": N, "confidence": 0.0-1.0}]'
    )

    try:
        content = await acall_llm(
            [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user_prompt}],
            temperature=0.3,
            timeout=60,
        )
        if content:
            return _parse(content)
    except Exception:
        pass
    return []
