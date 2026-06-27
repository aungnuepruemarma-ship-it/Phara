"""causal_candidates — identify candidate causal relationships from evidence text."""
from __future__ import annotations

import re
from dataclasses import dataclass


CAUSAL_PATTERNS = [
    (r"\b(\w[\w\s]{2,30})\s+causes?\s+(\w[\w\s]{2,30})", "causes"),
    (r"\b(\w[\w\s]{2,30})\s+leads?\s+to\s+(\w[\w\s]{2,30})", "causes"),
    (r"\b(\w[\w\s]{2,30})\s+enables?\s+(\w[\w\s]{2,30})", "enables"),
    (r"\b(\w[\w\s]{2,30})\s+inhibits?\s+(\w[\w\s]{2,30})", "inhibits"),
    (r"\b(\w[\w\s]{2,30})\s+increases?\s+(\w[\w\s]{2,30})", "increases"),
    (r"\b(\w[\w\s]{2,30})\s+decreases?\s+(\w[\w\s]{2,30})", "decreases"),
]


@dataclass
class CausalCandidate:
    cause: str
    effect: str
    relation: str
    source_text: str
    confidence: float = 0.4


def extract_causal_candidates(texts: list[str]) -> list[CausalCandidate]:
    """Extract candidate causal relationships from a list of text passages."""
    results: list[CausalCandidate] = []
    for text in texts:
        for pattern, relation in CAUSAL_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                cause = match.group(1).strip()[:80]
                effect = match.group(2).strip()[:80]
                if len(cause) > 3 and len(effect) > 3:
                    results.append(CausalCandidate(
                        cause=cause,
                        effect=effect,
                        relation=relation,
                        source_text=text[:200],
                    ))
    return results
