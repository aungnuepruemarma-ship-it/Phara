"""Motif miner — finds recurring operator subsequences in successful traces.

A candidate macro is an n-gram (len 2..max_len) that appears across multiple
successful traces and correlates with high gain. Mining only PROPOSES; the
certifier decides what is kept.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from .core import SolveResult


@dataclass
class Motif:
    sequence: Tuple[str, ...]
    support: int
    avg_gain: float
    avg_len: float

    @property
    def name(self) -> str:
        return "macro_" + "_".join(self.sequence)


def _ngrams(trace: List[str], max_len: int) -> Iterable[Tuple[str, ...]]:
    n = len(trace)
    for L in range(2, max_len + 1):
        for i in range(0, n - L + 1):
            yield tuple(trace[i:i + L])


def mine(successful: List[SolveResult], gain_fn, min_support: int = 2,
         min_gain: float = 1.0, max_len: int = 3) -> List[Motif]:
    stats: Dict[Tuple[str, ...], List[Tuple[int, float]]] = {}
    for run in successful:
        gain = gain_fn(run.states)
        seen_local = set()
        for gram in _ngrams(run.trace, max_len):
            if gram in seen_local:
                continue
            seen_local.add(gram)
            stats.setdefault(gram, []).append((len(run.trace), gain))

    motifs: List[Motif] = []
    for seq, vals in stats.items():
        support = len(vals)
        if support < min_support:
            continue
        avg_gain = sum(v[1] for v in vals) / support
        if avg_gain < min_gain:
            continue
        avg_len = sum(v[0] for v in vals) / support
        motifs.append(Motif(sequence=seq, support=support, avg_gain=avg_gain, avg_len=avg_len))

    # Strongest, shortest first.
    motifs.sort(key=lambda m: (-m.support, -m.avg_gain, len(m.sequence), m.name))
    return motifs
