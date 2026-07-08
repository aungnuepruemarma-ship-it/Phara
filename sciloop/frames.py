"""Frames — a 'way of thinking' as a first-class, mutable, heritable value.

A Frame bundles the structural choices that causally determine how the system
reasons: which certified forward macros it carries per domain, and which
goal-side decomposition policy it uses. (Attended observables ride along for
concept formation and introspection; they do not silently alter solving.)

fitness() is multi-domain with a uniformity bonus, so evolution rewards
domain-GENERAL minds, not specialists. Evolution selects on the TRAIN split;
final verdicts are always read on held-out TEST tasks.
"""
from __future__ import annotations

import json
import math
import random
from typing import Dict, List

from .adjoint import GoalAdapter, co_policies, solve_with_policy
from .icgg import runner as icgg_runner
from .icgg.core import Grammar
from .icgg.domains import get_domain

DOMAINS = ["arith", "strings", "vector"]


# ── the gene pool of certified forward macros (per domain) ────────────────────
_MACRO_POOL: Dict[str, List[List[str]]] | None = None


def macro_pool(seeds: int = 3) -> Dict[str, List[List[str]]]:
    """Certified macros per domain (via the existing ICGG pipeline). Only
    certified structure may enter the gene pool."""
    global _MACRO_POOL
    if _MACRO_POOL is None:
        pool: Dict[str, List[List[str]]] = {}
        for d in DOMAINS:
            res = icgg_runner.run_growth(d, generations=1, seeds=seeds)
            pool[d] = [c["sequence"] for c in res["certified_operators"]][:4]
        _MACRO_POOL = pool
    return _MACRO_POOL


# ── frame construction ────────────────────────────────────────────────────────
def default_frame() -> dict:
    """The hand-built frame: ALL certified macros + ONE GLOBAL adjoint v2
    policy. (The single global policy IS the designed artifact — evolved
    frames may specialize a different policy per domain, a dimension the
    designer never tuned.)"""
    pool = macro_pool()
    g = _policy_index({"schema": "regress_adaptive", "phi": 0.0, "R": 2})
    return {
        "id": "hand_built",
        "macro_mask": {d: [1] * len(pool[d]) for d in DOMAINS},
        "policy_idx": {d: g for d in DOMAINS},
        "attends": ["branch", "openness", "reach"],
        "lineage": [],
    }


def random_frame(rng: random.Random, fid: str) -> dict:
    pool = macro_pool()
    return {
        "id": fid,
        "macro_mask": {d: [rng.randint(0, 1) for _ in pool[d]] for d in DOMAINS},
        "policy_idx": {d: rng.randrange(len(co_policies())) for d in DOMAINS},
        "attends": ["branch", "openness", "reach"],
        "lineage": [],
    }


def _policy_index(policy: dict) -> int:
    for i, p in enumerate(co_policies()):
        if p == policy:
            return i
    return 0


def frame_policy(frame: dict, domain_name: str) -> dict:
    idx = frame["policy_idx"]
    i = idx[domain_name] if isinstance(idx, dict) else idx
    return co_policies()[i % len(co_policies())]


def frame_grammar(frame: dict, domain_name: str) -> Grammar:
    g = get_domain(domain_name).base_grammar()
    pool = macro_pool()
    for on, seq in zip(frame["macro_mask"][domain_name], pool[domain_name]):
        if on:
            g.add_macro("macro_" + "_".join(seq), seq)
    return g


def describe(frame: dict) -> str:
    pols = []
    for d in DOMAINS:
        p = frame_policy(frame, d)
        pols.append(f"{d}:{p['schema']}(R={p['R']})")
    n_macros = sum(sum(m) for m in frame["macro_mask"].values())
    return f"policies[{' '.join(pols)}] macros={n_macros}"


def fingerprint(frame: dict) -> str:
    return json.dumps({"m": frame["macro_mask"], "p": frame["policy_idx"]}, sort_keys=True)


# ── fitness ───────────────────────────────────────────────────────────────────
def fitness(frame: dict, seeds: List[int], split: str = "train", n: int = 12) -> dict:
    """Per-domain score = solve_rate + 1/(1+ln(1+mean_expanded)). Overall =
    mean + 0.5*min (uniformity/transfer bonus)."""
    per: Dict[str, float] = {}
    for name in DOMAINS:
        pol = frame_policy(frame, name)
        dom, ad = get_domain(name), GoalAdapter(name)
        g = frame_grammar(frame, name)
        total, solved, count = 0, 0, 0
        for s in seeds:
            for S, T in dom.tasks(n, seed=s, split=split):
                ok, exp, _ = solve_with_policy(dom, ad, S, T, pol, grammar=g)
                total += exp
                solved += 1 if ok else 0
                count += 1
        mean_exp = total / max(1, count)
        per[name] = (solved / max(1, count)) + 1.0 / (1.0 + math.log(1.0 + mean_exp))
    vals = list(per.values())
    overall = sum(vals) / len(vals) + 0.5 * min(vals)
    return {"overall": round(overall, 4), "per_domain": {k: round(v, 4) for k, v in per.items()}}
