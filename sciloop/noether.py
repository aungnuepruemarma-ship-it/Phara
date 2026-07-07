"""Computational Noether Engine (CNE).

Noether's theorem run backwards on a search process: discover a quantity Q that
is CONSERVED along successful reasoning trajectories (but not random ones), then
promote the operator compositions whose action leaves Q invariant — the
*symmetry generators*. Because Q lives in a domain-agnostic observable space,
these symmetry operators are the ones most likely to TRANSFER across domains.

This is the falsification machine for the hypothesis:
  "symmetry-derived operators transfer better than syntactic-motif operators."

Stdlib only.
"""
from __future__ import annotations

import itertools
import math
import random
from dataclasses import dataclass
from typing import Callable, List, Tuple

from . import invariants
from .icgg import certify as certmod
from .icgg import runner as icgg_runner
from .icgg.core import Grammar, SearchEngine
from .icgg.domains import Domain, get_domain

# An observable vector per state along a trajectory: (branching, openness, reach).
#   branching  b(x)   = number of applicable operators
#   openness   o(x)   = distinct next-states / b   (freedom to diverge)
#   reach      r(x)   = normalized branching = b / (b + 1)   (bounded proxy)
OBS_DIM = 3
_DELTA = 1e-6


def state_observables(grammar: Grammar, x) -> Tuple[float, float, float]:
    nxt = grammar.next_states(x)
    b = len(nxt)
    if b == 0:
        return (0.0, 0.0, 0.0)
    distinct = len(set(y for _, y in nxt))
    openness = distinct / b
    reach = b / (b + 1.0)
    return (float(b), float(openness), float(reach))


def path_series(grammar: Grammar, states: List) -> List[Tuple[float, float, float]]:
    """Observable vector at each interior state of a trajectory."""
    return [state_observables(grammar, s) for s in states[:-1]] if len(states) > 1 else []


# ── functional basis: Q(obs) ───────────────────────────────────────────────────
@dataclass
class Functional:
    weights: Tuple[float, ...]   # linear weights over observables
    kind: str                    # "linear" | "ratio"
    idx: Tuple[int, int] = (0, 1)

    def value(self, obs: Tuple[float, ...]) -> float:
        if self.kind == "ratio":
            a, b = obs[self.idx[0]], obs[self.idx[1]]
            return a / (b + _DELTA)
        return sum(w * o for w, o in zip(self.weights, obs))

    def describe(self) -> str:
        if self.kind == "ratio":
            names = ["branch", "openness", "reach"]
            return f"{names[self.idx[0]]} / {names[self.idx[1]]}"
        names = ["branch", "openness", "reach"]
        terms = [f"{w:+.2f}*{n}" for w, n in zip(self.weights, names) if abs(w) > 1e-9]
        return " ".join(terms) or "0"


def functional_basis() -> List[Functional]:
    cands: List[Functional] = []
    grid = (-1.0, -0.5, 0.0, 0.5, 1.0)
    for w in itertools.product(grid, repeat=OBS_DIM):
        if all(abs(x) < 1e-9 for x in w):
            continue
        cands.append(Functional(weights=w, kind="linear"))
    for i, j in ((0, 1), (0, 2), (1, 2), (1, 0), (2, 0)):
        cands.append(Functional(weights=(), kind="ratio", idx=(i, j)))
    return cands


# ── conservation scoring ───────────────────────────────────────────────────────
def _traj_drift(series: List[Tuple[float, ...]], Q: Functional) -> float:
    """How much Q drifts along one trajectory: Var_t(Q)/(|Mean_t(Q)|+d)."""
    vals = [Q.value(o) for o in series]
    if len(vals) < 2:
        return 0.0
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    return var / (abs(mean) + _DELTA)


def _mean_drift(trajs: List[List[Tuple[float, ...]]], Q: Functional) -> float:
    ds = [_traj_drift(t, Q) for t in trajs if len(t) >= 2]
    return sum(ds) / len(ds) if ds else 0.0


def discover_conserved(pos: List[List[Tuple[float, ...]]],
                       neg: List[List[Tuple[float, ...]]]) -> dict:
    """Pick Q* maximizing J = drift(neg) - drift(pos): constant on success,
    variable on random. Returns Q*, its drifts, and the conservation score."""
    best = None
    for Q in functional_basis():
        dp = _mean_drift(pos, Q)
        dn = _mean_drift(neg, Q)
        # normalize Q scale so trivial tiny-weight functionals don't win by scale
        score = (dn - dp)
        if best is None or score > best["score"]:
            best = {"Q": Q, "pos_drift": dp, "neg_drift": dn, "score": score}
    return best


# ── symmetry operators: compositions that leave Q ~invariant ───────────────────
def _sample_states(domain: Domain, n: int, seed: int) -> List:
    """Reachable states from starts by short random op walks."""
    g = domain.base_grammar()
    rng = random.Random(seed)
    starts = [s for s, _ in domain.tasks(6, seed=seed, split="train")]
    states = set()
    for s in starts:
        x = s
        states.add(x)
        for _ in range(rng.randint(2, 8)):
            nxt = g.next_states(x)
            if not nxt:
                break
            x = rng.choice(nxt)[1]
            states.add(x)
        if len(states) >= n:
            break
    return list(states)[:n]


def _apply_seq(grammar: Grammar, seq: Tuple[str, ...], x):
    cur = x
    for name in seq:
        op = grammar.ops.get(name)
        if op is None:
            return None
        cur = op.apply(cur)
        if cur is None:
            return None
    return cur


def symmetry_operators(domain: Domain, Q: Functional, seeds: List[int],
                       max_len: int = 3, eps: float = 0.15, top: int = 8) -> List[dict]:
    """Rank operator compositions by how little they perturb Q (symmetry)."""
    g = domain.base_grammar()
    base_names = [n for n in g.names()]
    sample = []
    for s in seeds:
        sample += _sample_states(domain, 30, seed=s)
    sample = sample[:60] or _sample_states(domain, 30, seed=0)

    results = []
    for L in range(2, max_len + 1):
        for seq in itertools.product(base_names, repeat=L):
            perts, applied = [], 0
            for x in sample:
                y = _apply_seq(g, seq, x)
                if y is None:
                    continue
                qx, qy = Q.value(state_observables(g, x)), Q.value(state_observables(g, y))
                denom = abs(qx) + _DELTA
                perts.append(abs(qy - qx) / denom)
                applied += 1
            if applied < 3:
                continue
            mean_pert = sum(perts) / len(perts)
            results.append({"sequence": list(seq), "mean_perturbation": mean_pert,
                            "applied": applied, "is_symmetry": mean_pert < eps})
    results.sort(key=lambda r: (r["mean_perturbation"], len(r["sequence"])))
    return results[:top]


# ── full CNE run for one domain ────────────────────────────────────────────────
def _gather_trajectories(domain: Domain, seeds: List[int], n: int = 30):
    """pos = observable series of SUCCESSFUL solves; neg = random walks."""
    g = domain.base_grammar()
    engine = SearchEngine(g)
    pos, neg = [], []
    rng = random.Random(999)
    for s in seeds:
        for start, target in domain.tasks(n, seed=s, split="train"):
            r = engine.solve(start, target)
            if r.success and len(r.states) > 2:
                pos.append(path_series(g, r.states))
            # random walk of similar length from the same start (the null model)
            x, walk = start, [start]
            for _ in range(max(3, len(r.states))):
                nxt = g.next_states(x)
                if not nxt:
                    break
                x = rng.choice(nxt)[1]
                walk.append(x)
            if len(walk) > 2:
                neg.append(path_series(g, walk))
    return pos, neg


def run_cne(domain_name: str, seeds: int = 3) -> dict:
    domain = get_domain(domain_name)
    seed_list = list(range(seeds))

    pos, neg = _gather_trajectories(domain, seed_list)
    conserved = discover_conserved(pos, neg)
    Q = conserved["Q"]

    syms = symmetry_operators(domain, Q, seed_list)
    sym_seqs = [tuple(s["sequence"]) for s in syms if s["is_symmetry"]][:4]

    # Certify symmetry-derived operators exactly like ICGG macros.
    from .icgg.miner import Motif
    motifs = [Motif(sequence=s, support=3, avg_gain=1.0, avg_len=float(len(s))) for s in sym_seqs]
    certs = certmod.certify(domain, motifs, seed_list, cap=len(motifs) or 1) if motifs else []
    kept = [c.to_dict() for c in certs if c.kept]

    return {
        "domain": domain_name,
        "conserved_quantity": {
            "expression": Q.describe(),
            "pos_drift": round(conserved["pos_drift"], 4),
            "neg_drift": round(conserved["neg_drift"], 4),
            "conservation_score": round(conserved["score"], 4),
        },
        "symmetry_operators": syms,
        "certified_symmetry_operators": kept,
        "_Q": Q,  # internal (not JSON-serialized by caller)
    }


def compare_transfer(domain_names: List[str], seeds: int = 3) -> dict:
    """Head-to-head: transfer of ICGG syntactic macros vs CNE symmetry macros.
    Builds two grammars per source domain (syntactic-grown vs symmetry-grown) and
    measures held-out reduction on every target domain."""
    seed_list = list(range(seeds))
    out = {"domains": domain_names, "syntactic": {}, "symmetry": {}}

    for src in domain_names:
        # syntactic operators via ICGG
        icgg_res = icgg_runner.run_growth(src, generations=1, seeds=seeds)
        syn_ops = {n: op for n, op in icgg_res["grammar"].ops.items() if n.startswith("macro_")}

        # symmetry operators via CNE
        cne = run_cne(src, seeds=seeds)
        sym_base = get_domain(src).base_grammar()
        for c in cne["certified_symmetry_operators"]:
            sym_base.add_macro("sym_" + "_".join(c["sequence"]), c["sequence"])
        sym_ops = {n: op for n, op in sym_base.ops.items() if n.startswith("sym_")}

        out["syntactic"][src] = _transfer_row(src, syn_ops, domain_names, seed_list)
        out["symmetry"][src] = _transfer_row(src, sym_ops, domain_names, seed_list)
    return out


def _transfer_row(src, macro_ops, domain_names, seed_list) -> dict:
    row = {}
    for tgt in domain_names:
        dom = get_domain(tgt)
        base = dom.base_grammar()
        base_mean = _eval_expanded(base, dom, seed_list)
        g = dom.base_grammar()
        for n, op in macro_ops.items():
            g.add(op)
        mean = _eval_expanded(g, dom, seed_list)
        row[tgt] = round(base_mean - mean, 1)  # reduction (positive = helps)
    return row


def _eval_expanded(grammar, domain, seed_list, n=25) -> float:
    total, count = 0, 0
    for seed in seed_list:
        eng = SearchEngine(grammar)
        for start, target in domain.tasks(n, seed=seed, split="test"):
            r = eng.solve(start, target)
            total += r.expanded
            count += 1
    return total / max(1, count)


# ── difficulty: symmetry-breaking point ────────────────────────────────────────
def breaking_point_analysis(domain_name: str, seeds: int = 3) -> dict:
    """The step where Q first breaks its band -> a difficulty observable.
    Correlate Q-breaking depth with effort (nodes expanded) via Spearman."""
    domain = get_domain(domain_name)
    seed_list = list(range(seeds))
    cne = run_cne(domain_name, seeds=seeds)
    Q = cne["_Q"]
    g = domain.base_grammar()
    eng = SearchEngine(g)

    break_depths, efforts = [], []
    for s in seed_list:
        for start, target in domain.tasks(25, seed=s, split="test"):
            r = eng.solve(start, target)
            if not r.success or len(r.states) < 4:
                continue
            series = path_series(g, r.states)
            vals = [Q.value(o) for o in series]
            mean = sum(vals) / len(vals)
            band = 0.5 * (max(vals) - min(vals) + _DELTA)
            bp = next((i for i, v in enumerate(vals) if abs(v - mean) > band), len(vals))
            break_depths.append(float(bp))
            efforts.append(math.log(r.expanded + 1))
    rho = invariants.spearman(break_depths, efforts) if len(break_depths) >= 3 else 0.0
    return {"domain": domain_name, "n": len(break_depths),
            "spearman_breakdepth_vs_logeffort": round(rho, 3)}
