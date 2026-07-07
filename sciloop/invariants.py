"""Invariant Discovery — observable battery over execution geometry/traces.

Each observable is a pure function of a geometry dict (from geometry.py) or a
numeric series. Plus:
  spearman()         — rank correlation (hand-rolled, stdlib)
  coarse_grain_R()   — finite-scale stability R = 1 - Var(Q2,Q4,Q8)/(Mean+d)
                       (an observable with R ~ 1 survives coarsening).
"""
from __future__ import annotations

import math
from typing import Dict, List


# ── observables over a geometry dict ──────────────────────────────────────────
def obs_ast_complexity(geom: dict) -> float:
    return float(geom.get("ast_nodes", 0))


def obs_branching(geom: dict) -> float:
    """Mean out-degree of the dynamic call graph (structural branching)."""
    edges = geom.get("call_graph") or {}
    counts = geom.get("call_counts") or {}
    if not counts:
        return 0.0
    return len(edges) / max(1, len(counts))


def obs_recursion_depth(geom: dict) -> float:
    return float(geom.get("max_call_depth", 0))


def obs_work_ratio(geom: dict) -> float:
    """Dynamic events per distinct line — how much a program 'churns' its code."""
    events = geom.get("total_line_events", 0)
    lines = max(1, geom.get("distinct_lines", 1))
    return events / lines


def obs_coherence_CF(geom: dict) -> float:
    """C/F proxy: fraction of call events concentrated in the top function
    (forced/dominant structure) vs spread (free). 1.0 = fully dominated."""
    counts = geom.get("call_counts") or {}
    if not counts:
        return 0.0
    vals = sorted(counts.values(), reverse=True)
    return vals[0] / max(1, sum(vals))


OBSERVABLES = {
    "ast_complexity": obs_ast_complexity,
    "branching": obs_branching,
    "recursion_depth": obs_recursion_depth,
    "work_ratio": obs_work_ratio,
    "coherence_CF": obs_coherence_CF,
}


def extract(geom: dict) -> Dict[str, float]:
    if not geom:
        return {k: 0.0 for k in OBSERVABLES}
    return {k: float(fn(geom)) for k, fn in OBSERVABLES.items()}


# ── statistics (stdlib) ───────────────────────────────────────────────────────
def _rank(xs: List[float]) -> List[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman(xs: List[float], ys: List[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 3:
        return 0.0
    rx, ry = _rank(xs), _rank(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    vx = math.sqrt(sum((r - mx) ** 2 for r in rx))
    vy = math.sqrt(sum((r - my) ** 2 for r in ry))
    if vx == 0 or vy == 0:
        return 0.0
    return cov / (vx * vy)


def coarse_grain_R(series: List[float], delta: float = 1e-6) -> float:
    """Coarse-grain a per-step series by 2/4/8 (block means), then measure how
    stable the mean-of-blocks statistic is across scales."""
    if len(series) < 8:
        return 0.0

    def block_mean(s: List[float], k: int) -> float:
        blocks = [s[i:i + k] for i in range(0, len(s), k)]
        means = [sum(b) / len(b) for b in blocks if b]
        return sum(means) / len(means) if means else 0.0

    q2, q4, q8 = block_mean(series, 2), block_mean(series, 4), block_mean(series, 8)
    qs = [q2, q4, q8]
    mean = sum(qs) / 3
    var = sum((q - mean) ** 2 for q in qs) / 3
    return 1.0 - var / (abs(mean) + delta)
