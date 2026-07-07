"""The Adjoint Engine — learning on the goal side of the adjunction.

Thesis under test: forward operators (state -> state) are welded to their
domain's carrier and cannot transfer (measured: ICGG macros transfer = 0.0
off-diagonal). CO-operators — goal decompositions (goal -> subgoals) — are
expressed over the *structure of specifications* (interpolation, projection,
regression), which every domain shares. So a decomposition POLICY learned on
one domain should transfer unchanged to others.

A goal is reach(S, T). Co-operator schemas (domain-generic):
  waypoint(phi) : reach(S,T) -> reach(S,M) ; reach(M,T),  M = interpolate(S,T,phi)
  peel          : reach(S,T) -> reach(S,P) ; reach(P,T),  P = project one component
  regress       : reach(S,T) -> reach(S,T') ; final-op,   T' = pull T back one step

A POLICY = (schema, phi, R) where R = recursion depth (scale-free, so the same
policy is meaningful in every domain). Learning = pick the policy minimizing
held-out-style expanded nodes on the SOURCE domain's train tasks. Transfer =
apply that exact policy to the other domains' test tasks.

Honest accounting: every node expanded in every sub-search counts; if any
subgoal fails, we fall back to plain BFS on the original goal and ALSO count
the wasted work. Solutions are replay-verified end to end.
"""
from __future__ import annotations

import random
from typing import Callable, List, Optional, Tuple

from .icgg.core import Grammar, SearchEngine
from .icgg.domains import Domain, get_domain

_MAX_EXPANDED = 20000
_MAX_DEPTH = 14


# ── goal-structure adapters (expose goal STRUCTURE, not solutions) ────────────
class GoalAdapter:
    """Interpolation / projection / regression over the goal space."""

    def __init__(self, name: str):
        self.name = name

    def interpolate(self, S, T, phi: float):
        if self.name == "arith":
            M = int(round(S + (T - S) * phi))
            return M if M not in (S, T) and M > 0 else None
        if self.name == "strings":
            if T.startswith(S):
                rest = T[len(S):]
                k = int(round(len(rest) * phi))
                if 0 < k < len(rest):
                    return S + rest[:k]
                return None
            k = int(round(len(T) * phi))
            return T[:k] if 0 < k < len(T) else None
        if self.name == "vector":
            M = (int(round(S[0] + (T[0] - S[0]) * phi)),
                 int(round(S[1] + (T[1] - S[1]) * phi)))
            return M if M not in (S, T) else None
        return None

    def project(self, S, T):
        """Achieve one 'component' of T first (it-suffices-to-solve-coordinatewise)."""
        if self.name == "arith":
            # component = scale: nearest power of two at/below T
            if T <= 2:
                return None
            p = 1
            while p * 2 <= T:
                p *= 2
            return p if p not in (S, T) else None
        if self.name == "strings":
            # component = length: reach a string of the right length (T's prefix)
            k = len(T) - 1
            return T[:k] if 0 < k < len(T) and T[:k] != S else None
        if self.name == "vector":
            P = (T[0], S[1])  # x first, then y
            return P if P not in (S, T) else None
        return None

    def distance(self, S, T) -> float:
        """Scale estimate of goal size — used by the ADAPTIVE policy to decide
        when a subgoal is small enough to hand to plain search."""
        if self.name == "arith":
            return abs(T - S)
        if self.name == "strings":
            return (len(T) - len(S)) if T.startswith(S) else (len(T) + 1)
        if self.name == "vector":
            return abs(T[0] - S[0]) + abs(T[1] - S[1])
        return 0.0

    def regress(self, T):
        """Pull the goal back one step: candidate (T', final_op_name) pairs."""
        if self.name == "arith":
            out = []
            if T % 2 == 0 and T // 2 > 0:
                out.append((T // 2, "double"))
            if T % 3 == 0 and T // 3 > 0:
                out.append((T // 3, "triple"))
            if T - 1 > 0:
                out.append((T - 1, "add1"))
            return out
        if self.name == "strings":
            out = []
            if T and T[-1] == "a":
                out.append((T[:-1], "app_a"))
            if T and T[-1] == "b":
                out.append((T[:-1], "app_b"))
            n = len(T)
            if n >= 2 and n % 2 == 0 and T[:n // 2] == T[n // 2:]:
                out.append((T[:n // 2], "dup"))
            return out
        if self.name == "vector":
            x, y = T
            out = []
            if x >= 3:
                out.append(((x - 3, y), "jump_r"))
            if y >= 3:
                out.append(((x, y - 3), "jump_u"))
            if x >= 1:
                out.append(((x - 1, y), "right"))
            if y >= 1:
                out.append(((x, y - 1), "up"))
            return out
        return []


# ── policies (the learnable goal-side object) ─────────────────────────────────
def co_policies() -> List[dict]:
    pols = []
    for phi in (0.25, 0.5, 0.75):
        for R in (1, 2, 3):
            pols.append({"schema": "waypoint", "phi": phi, "R": R})
    for R in (1, 2, 3):
        pols.append({"schema": "peel", "phi": 0.0, "R": R})
    for R in (2, 4, 6):
        pols.append({"schema": "regress", "phi": 0.0, "R": R})
    # v2: ADAPTIVE regression — recurse until the goal is smaller than leaf
    # size R, instead of a fixed number of steps. Scale-free across goal sizes.
    for R in (2, 4, 8):
        pols.append({"schema": "regress_adaptive", "phi": 0.0, "R": R})
    return pols


def policy_name(p: dict) -> str:
    return f"co_{p['schema']}_phi{p['phi']}_R{p['R']}"


# ── the co-search: decompose goals, BFS the leaves, verify the whole ──────────
def _bfs(engine: SearchEngine, S, T):
    r = engine.solve(S, T)
    return r.success, r.expanded, list(r.trace)


def solve_with_policy(domain: Domain, adapter: GoalAdapter, S, T,
                      policy: dict) -> Tuple[bool, int, List[str]]:
    """Returns (success, total_expanded, verified op trace)."""
    g = domain.base_grammar()
    engine = SearchEngine(g, max_depth=_MAX_DEPTH, max_expanded=_MAX_EXPANDED)
    spent = 0

    def leaf(a, b):
        nonlocal spent
        ok, exp, tr = _bfs(engine, a, b)
        spent += exp
        return ok, tr

    def regress_adaptive(a, b, leaf_size: float) -> Optional[List[str]]:
        """Greedily pull the goal backward until it is within leaf_size of the
        start, then hand the small residual to plain search. Linear cost in
        goal size (no branch backtracking), scale-free in R."""
        suffix: List[str] = []
        cur = b
        for _ in range(256):
            if adapter.distance(a, cur) <= leaf_size:
                break
            cands = adapter.regress(cur)
            if not cands:
                break
            Tp, opname = cands[0]
            suffix.append(opname)
            cur = Tp
        ok, tr = leaf(a, cur)
        if not ok:
            return None
        return tr + list(reversed(suffix))

    def rec(a, b, depth) -> Optional[List[str]]:
        if a == b:
            return []
        if policy["schema"] == "regress_adaptive":
            return regress_adaptive(a, b, float(policy["R"]))
        if depth <= 0:
            ok, tr = leaf(a, b)
            return tr if ok else None

        if policy["schema"] == "waypoint":
            M = adapter.interpolate(a, b, policy["phi"])
            if M is None:
                ok, tr = leaf(a, b)
                return tr if ok else None
            left = rec(a, M, depth - 1)
            if left is None:
                return None
            right = rec(M, b, depth - 1)
            if right is None:
                return None
            return left + right

        if policy["schema"] == "peel":
            P = adapter.project(a, b)
            if P is None:
                ok, tr = leaf(a, b)
                return tr if ok else None
            left = rec(a, P, depth - 1)
            if left is None:
                return None
            right = rec(P, b, depth - 1)
            if right is None:
                return None
            return left + right

        if policy["schema"] == "regress":
            for (Tp, opname) in adapter.regress(b):
                sub = rec(a, Tp, depth - 1)
                if sub is not None:
                    return sub + [opname]
            ok, tr = leaf(a, b)
            return tr if ok else None

        ok, tr = leaf(a, b)
        return tr if ok else None

    trace = rec(S, T, policy["R"])
    if trace is None:
        # decomposition failed -> honest fallback: plain BFS on the whole goal,
        # and the wasted decomposition work still counts.
        ok, tr = leaf(S, T)
        if not ok:
            return False, spent, []
        trace = tr

    # replay-verify the whole solution
    cur = S
    for opname in trace:
        op = g.ops.get(opname)
        cur = op.apply(cur) if op else None
        if cur is None:
            return False, spent, []
    return (cur == T), spent, trace


# ── learning (source domain) and evaluation (all domains) ─────────────────────
def _eval_policy(domain: Domain, adapter: GoalAdapter, policy: Optional[dict],
                 seeds: List[int], split: str, n: int = 20) -> dict:
    g = domain.base_grammar()
    engine = SearchEngine(g, max_depth=_MAX_DEPTH, max_expanded=_MAX_EXPANDED)
    total, solved, count = 0, 0, 0
    for s in seeds:
        for S, T in domain.tasks(n, seed=s, split=split):
            if policy is None:
                ok, exp, _ = _bfs(engine, S, T)
            else:
                ok, exp, _ = solve_with_policy(domain, adapter, S, T, policy)
            total += exp
            solved += 1 if ok else 0
            count += 1
    return {"mean_expanded": total / max(1, count), "solve_rate": solved / max(1, count)}


def learn_policy(domain_name: str, seeds: int = 3) -> dict:
    """Pick the goal-side policy minimizing expanded nodes on SOURCE train tasks
    (solve-rate must not drop below base)."""
    domain = get_domain(domain_name)
    adapter = GoalAdapter(domain_name)
    seed_list = list(range(seeds))

    base = _eval_policy(domain, adapter, None, seed_list, "train")
    best = None
    for p in co_policies():
        r = _eval_policy(domain, adapter, p, seed_list, "train")
        if r["solve_rate"] < base["solve_rate"] - 1e-9:
            continue
        if best is None or r["mean_expanded"] < best["stats"]["mean_expanded"]:
            best = {"policy": p, "stats": r}
    return {"domain": domain_name, "base_train": base, "learned": best}


def adjoint_experiment(domain_names: List[str], seeds: int = 3) -> dict:
    """The head-to-head. For each SOURCE domain: learn a goal-side policy on its
    train split, then evaluate that EXACT policy on every domain's TEST split.
    Controls: base BFS (no decomposition) and a random policy (3 draws)."""
    seed_list = list(range(seeds))
    rng = random.Random(7)

    base_test = {}
    for name in domain_names:
        d, a = get_domain(name), GoalAdapter(name)
        base_test[name] = _eval_policy(d, a, None, seed_list, "test")

    out = {"domains": domain_names, "base_test": base_test,
           "learned_policies": {}, "goal_side": {}, "random_control": {}}

    for src in domain_names:
        learned = learn_policy(src, seeds=seeds)
        pol = learned["learned"]["policy"] if learned["learned"] else None
        out["learned_policies"][src] = pol
        row = {}
        for tgt in domain_names:
            d, a = get_domain(tgt), GoalAdapter(tgt)
            r = _eval_policy(d, a, pol, seed_list, "test") if pol else base_test[tgt]
            row[tgt] = {
                "mean_expanded": round(r["mean_expanded"], 1),
                "solve_rate": round(r["solve_rate"], 2),
                "reduction": round(base_test[tgt]["mean_expanded"] - r["mean_expanded"], 1),
            }
        out["goal_side"][src] = row

    # random-policy control, averaged over 3 draws, evaluated everywhere
    for tgt in domain_names:
        d, a = get_domain(tgt), GoalAdapter(tgt)
        reds = []
        for _ in range(3):
            p = rng.choice(co_policies())
            r = _eval_policy(d, a, p, seed_list, "test")
            reds.append(base_test[tgt]["mean_expanded"] - r["mean_expanded"])
        out["random_control"][tgt] = round(sum(reds) / len(reds), 1)

    return out
