"""Concept invention — the engine coins its own terms and they must earn them.

A candidate concept is a named predicate over per-step trace observables
(threshold on a Noether-basis functional). Its per-trace feature is the
fraction of steps where it holds. Admission on HELD-OUT traces requires either:
  prediction: |Spearman(feature, log effort)| beats the best raw observable
              by >= 0.10, or
  compression: labeling traces hard/easy via the concept saves MDL bits
               (information gain * n) beyond the cost of defining it.
Admitted concepts become inputs to LEVEL-2 proposals (conjunctions) — the
concept tower. Every admission/rejection is logged with its reason.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

from . import invariants
from .noether import Functional, functional_basis, path_series
from .icgg.core import SearchEngine
from .icgg.domains import get_domain

DOMAINS = ["arith", "strings", "vector"]
_OBS_NAMES = ["branch", "openness", "reach"]


# ── data: (per-step obs series, log effort) per trace ─────────────────────────
def _gather(domain_name: str, seeds: List[int], split: str, n: int = 20):
    dom = get_domain(domain_name)
    g = dom.base_grammar()
    eng = SearchEngine(g)
    out = []
    for s in seeds:
        for S, T in dom.tasks(n, seed=s, split=split):
            r = eng.solve(S, T)
            if r.success and len(r.states) > 2:
                out.append((path_series(g, r.states), math.log(r.expanded + 1)))
    return out


# ── concepts ──────────────────────────────────────────────────────────────────
class Concept:
    def __init__(self, name: str, Q: Functional, theta: float,
                 built_from: List[str] | None = None, level: int = 1):
        self.name = name
        self.Q = Q
        self.theta = theta
        self.built_from = built_from or []
        self.level = level

    def holds(self, obs) -> bool:
        return self.Q.value(obs) > self.theta

    def feature(self, series) -> float:
        if not series:
            return 0.0
        return sum(1 for o in series if self.holds(o)) / len(series)

    def describe(self) -> str:
        return f"{self.name}: [{self.Q.describe()}] > {self.theta:.3f} (level {self.level})"


def _spearman_feature(data, feat_fn) -> float:
    xs = [feat_fn(series) for series, _ in data]
    ys = [y for _, y in data]
    return invariants.spearman(xs, ys)


def _baseline_rho(data) -> Tuple[str, float]:
    """Best |Spearman| among the raw observables (the bar to beat)."""
    best = ("none", 0.0)
    for i, nm in enumerate(_OBS_NAMES):
        rho = abs(_spearman_feature(data, lambda s, i=i: sum(o[i] for o in s) / max(1, len(s))))
        if rho > best[1]:
            best = (nm, rho)
    return best


def _mdl_gain_bits(data, feat_fn) -> float:
    """Information gain (bits * n) of concept-split on the hard/easy outcome,
    minus a 32-bit definition cost."""
    ys = sorted(y for _, y in data)
    if len(ys) < 8:
        return -1.0
    median_y = ys[len(ys) // 2]
    feats = [feat_fn(series) for series, _ in data]
    fs = sorted(feats)
    median_f = fs[len(fs) // 2]

    def H(p):
        if p <= 0 or p >= 1:
            return 0.0
        return -p * math.log2(p) - (1 - p) * math.log2(1 - p)

    n = len(data)
    hard = [1 if y > median_y else 0 for _, y in data]
    p_hard = sum(hard) / n
    groups = {0: [], 1: []}
    for f, h in zip(feats, hard):
        groups[1 if f > median_f else 0].append(h)
    cond = 0.0
    for grp in groups.values():
        if grp:
            cond += (len(grp) / n) * H(sum(grp) / len(grp))
    return (H(p_hard) - cond) * n - 32.0


# ── invention: level 1 from the functional basis, level 2 from admitted ───────
def invent(seeds: int = 3) -> dict:
    seed_list = list(range(seeds))
    train = {d: _gather(d, seed_list, "train") for d in DOMAINS}
    test = {d: _gather(d, [s + 10 for s in seed_list], "test") for d in DOMAINS}
    all_test = [t for d in DOMAINS for t in test[d]]
    all_train = [t for d in DOMAINS for t in train[d]]

    base_name, base_rho = _baseline_rho(all_test)
    report = {"baseline": {"observable": base_name, "abs_rho": round(base_rho, 3)},
              "admitted": [], "rejected": [], "tower": []}
    admitted: List[Concept] = []

    # Level 1 — candidates from the Noether functional basis, thresholds from
    # train quantiles; admission judged on HELD-OUT traces only.
    # DIVERSITY RULE: a concept must be NEW INFORMATION — its train-split
    # feature must not be a synonym (|Spearman| >= 0.9) of an admitted one.
    cand_id = 0
    n_dupes = 0
    train_feats: List[List[float]] = []
    for Q in functional_basis():
        vals = sorted(Q.value(o) for series, _ in all_train for o in series)
        if len(vals) < 10:
            continue
        for qfrac in (0.25, 0.5, 0.75):
            theta = vals[int(len(vals) * qfrac)]
            c = Concept(f"C{cand_id}", Q, theta)
            cand_id += 1
            rho = abs(_spearman_feature(all_test, c.feature))
            mdl = _mdl_gain_bits(all_test, c.feature)
            passes = (rho >= base_rho + 0.10) or (mdl > 0)
            if not passes:
                continue
            tf = [c.feature(series) for series, _ in all_train]
            if any(abs(invariants.spearman(tf, prev)) >= 0.9 for prev in train_feats):
                n_dupes += 1
                continue  # synonym of an existing concept — not new knowledge
            train_feats.append(tf)
            why = (f"prediction: |rho|={rho:.3f} vs baseline {base_rho:.3f}"
                   if rho >= base_rho + 0.10 else f"compression: MDL gain {mdl:.1f} bits")
            c.name = f"C{len(admitted)+1}" + ("_pred" if "prediction" in why else "_mdl")
            admitted.append(c)
            report["admitted"].append({"concept": c.describe(), "why": why,
                                       "abs_rho": round(rho, 3)})
            if len(admitted) >= 8:
                break
        if len(admitted) >= 8:
            break
    report["rejected"].append(
        {"note": f"{cand_id - len(admitted) - n_dupes} candidates failed both tests "
                 f"(bar: |rho| >= {base_rho:.3f}+0.10 or MDL>0); "
                 f"{n_dupes} passed but were rejected as SYNONYMS of admitted concepts"})

    # Level 2 — combinations of admitted concepts (the tower). Must beat the
    # better parent on held-out prediction.
    def _and(a, b):
        def f(series):
            if not series:
                return 0.0
            return sum(1 for o in series if a.holds(o) and b.holds(o)) / len(series)
        return f, f"{a.name} AND {b.name}"

    def _andnot(a, b):
        def f(series):
            if not series:
                return 0.0
            return sum(1 for o in series if a.holds(o) and not b.holds(o)) / len(series)
        return f, f"{a.name} AND NOT {b.name}"

    for i in range(len(admitted)):
        for j in range(len(admitted)):
            if i == j:
                continue
            a, b = admitted[i], admitted[j]
            combos = [_and(a, b)] if i < j else []
            combos.append(_andnot(a, b))
            parent = max(abs(_spearman_feature(all_test, a.feature)),
                         abs(_spearman_feature(all_test, b.feature)))
            for feat, label in combos:
                rho2 = abs(_spearman_feature(all_test, feat))
                if rho2 > parent + 0.02:
                    report["tower"].append({
                        "concept": label, "built_from": [a.name, b.name], "level": 2,
                        "abs_rho": round(rho2, 3), "parent_best": round(parent, 3),
                    })
    report["tower"].sort(key=lambda t: -t["abs_rho"])
    report["tower"] = report["tower"][:5]
    return report
