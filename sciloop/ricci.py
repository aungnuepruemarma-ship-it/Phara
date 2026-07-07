"""Ricci Computing — the reachability graph of a search process has intrinsic
curvature; difficulty lives at negative-curvature bottlenecks; operators should
be placed where they bridge those bottlenecks.

Method (stdlib only):
  1. Build a sampled reachability graph of the domain (nodes=states,
     edges=op applications), undirected.
  2. Compute Forman-Ricci curvature per edge (closed-form combinatorial):
        F(x,y) = 4 - deg(x) - deg(y) + 3*|triangles(x,y)|
     Negative F  <=>  bottleneck / bridge-like edge.
  3. DIFFICULTY CLAIM: integrated negative curvature along a task's solution
     path predicts search effort (Spearman vs log expanded), with the SAME
     formula in every domain (coordinate-free).
  4. OPERATOR-PLACEMENT CLAIM: rank candidate operator compositions by how
     negatively curved the region they traverse is (bridge score) — using NO
     solution traces at all — then certify exactly like ICGG. A/B against
     frequency-mined macros (which require solved traces). If curvature-selected
     operators match frequency-mined performance with zero supervision, the
     geometric rule transfers across domains by construction.
"""
from __future__ import annotations

import itertools
import math
import random
from collections import deque
from typing import Dict, List, Set, Tuple

from . import invariants
from .icgg import certify as certmod
from .icgg.core import Grammar, SearchEngine
from .icgg.domains import Domain, get_domain
from .icgg.miner import Motif, mine

_DELTA = 1e-9


# ── 1. sampled reachability graph ─────────────────────────────────────────────
def build_graph(domain: Domain, seeds: List[int], max_nodes: int = 400) -> Dict:
    """BFS the reachability graph from task starts up to max_nodes.
    Returns {'adj': {state: set(neighbors)}, 'edges': [(x,y), ...]}."""
    g = domain.base_grammar()
    starts = []
    for s in seeds:
        starts += [st for st, _ in domain.tasks(8, seed=s, split="train")]

    adj: Dict[object, Set[object]] = {}
    q = deque(starts)
    seen = set(starts)
    while q and len(seen) < max_nodes:
        x = q.popleft()
        adj.setdefault(x, set())
        for _, y in g.next_states(x):
            adj.setdefault(y, set())
            adj[x].add(y)
            adj[y].add(x)  # undirected for curvature
            if y not in seen and len(seen) < max_nodes:
                seen.add(y)
                q.append(y)
    edges = []
    done = set()
    for x, nbrs in adj.items():
        for y in nbrs:
            key = (min(repr(x), repr(y)), max(repr(x), repr(y)))
            if key not in done:
                done.add(key)
                edges.append((x, y))
    return {"adj": adj, "edges": edges}


# ── 2. Forman–Ricci curvature ─────────────────────────────────────────────────
def forman_curvature(graph: Dict) -> Dict[Tuple, float]:
    adj = graph["adj"]
    curv: Dict[Tuple, float] = {}
    for x, y in graph["edges"]:
        tri = len(adj[x] & adj[y])
        curv[(x, y)] = 4.0 - len(adj[x]) - len(adj[y]) + 3.0 * tri
    return curv


def _edge_curv(curv: Dict, x, y) -> float | None:
    return curv.get((x, y), curv.get((y, x)))


def curvature_summary(curv: Dict[Tuple, float]) -> dict:
    vals = list(curv.values())
    if not vals:
        return {"edges": 0}
    neg = [v for v in vals if v < 0]
    return {
        "edges": len(vals),
        "mean": round(sum(vals) / len(vals), 3),
        "min": min(vals),
        "max": max(vals),
        "frac_negative": round(len(neg) / len(vals), 3),
    }


# ── 3. difficulty: path curvature vs effort ───────────────────────────────────
def difficulty_analysis(domain_name: str, seeds: int = 3, n_tasks: int = 25) -> dict:
    domain = get_domain(domain_name)
    seed_list = list(range(seeds))
    graph = build_graph(domain, seed_list)
    curv = forman_curvature(graph)

    g = domain.base_grammar()
    eng = SearchEngine(g)
    xs, ys = [], []  # x = integrated negative curvature along path, y = log effort
    for s in seed_list:
        for start, target in domain.tasks(n_tasks, seed=s, split="test"):
            r = eng.solve(start, target)
            if not r.success or len(r.states) < 3:
                continue
            path_curvs = []
            for a, b in zip(r.states, r.states[1:]):
                c = _edge_curv(curv, a, b)
                if c is not None:
                    path_curvs.append(c)
            if not path_curvs:
                continue
            neg_integral = -sum(min(0.0, c) for c in path_curvs) / len(path_curvs)
            xs.append(neg_integral)
            ys.append(math.log(r.expanded + 1))
    rho = invariants.spearman(xs, ys) if len(xs) >= 3 else 0.0
    return {"domain": domain_name, "n": len(xs),
            "curvature": curvature_summary(curv),
            "spearman_negcurv_vs_logeffort": round(rho, 3)}


# ── 4. curvature-placed operators (zero-supervision selection) ────────────────
def bridge_scores(domain: Domain, seeds: List[int], max_len: int = 3,
                  n_sample: int = 50) -> List[dict]:
    """Score candidate op-compositions by the negative curvature of the region
    they traverse. Uses ONLY the reachability graph — no solved traces."""
    g = domain.base_grammar()
    graph = build_graph(domain, seeds)
    curv = forman_curvature(graph)
    rng = random.Random(4242)
    sample = list(graph["adj"].keys())
    rng.shuffle(sample)
    sample = sample[:n_sample]

    names = g.names()
    results = []
    for L in range(2, max_len + 1):
        for seq in itertools.product(names, repeat=L):
            traversed, applied = [], 0
            for x in sample:
                cur, ok, local = x, True, []
                for opname in seq:
                    op = g.ops[opname]
                    nxt = op.apply(cur)
                    if nxt is None or nxt == cur:
                        ok = False
                        break
                    c = _edge_curv(curv, cur, nxt)
                    if c is not None:
                        local.append(c)
                    cur = nxt
                if ok and local:
                    applied += 1
                    traversed.append(sum(local) / len(local))
            if applied < 5:
                continue
            mean_curv = sum(traversed) / len(traversed)
            # Bridge score: how negatively curved is the traversed region
            results.append({
                "sequence": list(seq),
                "mean_traversed_curvature": round(mean_curv, 3),
                "bridge_score": round(-mean_curv, 3),
                "applicability": round(applied / max(1, len(sample)), 2),
            })
    results.sort(key=lambda r: (-r["bridge_score"], -r["applicability"], len(r["sequence"])))
    return results


def select_operators(domain_name: str, seeds: int = 3, top: int = 4) -> List[dict]:
    domain = get_domain(domain_name)
    scored = bridge_scores(domain, list(range(seeds)))
    return scored[:top]


# ── 5. the A/B: curvature-selected vs frequency-mined ─────────────────────────
def ab_compare(domain_names: List[str], seeds: int = 3) -> dict:
    """Same certification harness for both arms:
       ARM A (supervised): ICGG frequency mining — needs successful solve traces.
       ARM B (zero-shot geometric): curvature bridge rule — needs only the graph.
    The SAME rule runs unchanged on every domain (coordinate-free)."""
    seed_list = list(range(seeds))
    out = {"domains": domain_names, "arms": {}}

    for name in domain_names:
        domain = get_domain(name)

        # ARM A — frequency mining over successful traces (supervision)
        g = domain.base_grammar()
        eng = SearchEngine(g)
        succ = []
        for s in seed_list:
            for start, target in domain.tasks(30, seed=s, split="train"):
                r = eng.solve(start, target)
                if r.success:
                    succ.append(r)
        motifs_a = mine(succ, domain.gain, min_support=2, min_gain=1.0, max_len=3)[:4]
        certs_a = certmod.certify(domain, motifs_a, seed_list, cap=4)
        kept_a = [c.to_dict() for c in certs_a if c.kept]
        best_a = max([c["improvement"] for c in kept_a], default=0.0)

        # ARM B — curvature bridge rule (no solved traces used for selection)
        picks = select_operators(name, seeds=seeds, top=4)
        motifs_b = [Motif(sequence=tuple(p["sequence"]), support=3, avg_gain=1.0,
                          avg_len=float(len(p["sequence"]))) for p in picks]
        certs_b = certmod.certify(domain, motifs_b, seed_list, cap=4) if motifs_b else []
        kept_b = [c.to_dict() for c in certs_b if c.kept]
        best_b = max([c["improvement"] for c in kept_b], default=0.0)

        out["arms"][name] = {
            "frequency_supervised": {
                "kept": [c["name"] for c in kept_a],
                "best_improvement": round(best_a, 1),
            },
            "curvature_zero_shot": {
                "candidates": ["+".join(p["sequence"]) for p in picks],
                "kept": [c["name"] for c in kept_b],
                "best_improvement": round(best_b, 1),
            },
            "zero_shot_matches_supervised": bool(best_b >= 0.8 * best_a and best_b > 0),
        }
    return out
