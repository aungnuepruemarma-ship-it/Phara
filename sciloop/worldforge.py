"""World Forge + Lawmaker — the engine invents universes to attack its own
knowledge, then induces laws of reasoning across them.

FORGE: synthesize reasoning domains no human designed — operator algebras over
bounded integer-tuple states, built from invertible generator pairs (op,
inverse) plus one-way ops. Because inverses are known BY CONSTRUCTION, the
GoalAdapter (distance / interpolate / regress) is derived automatically, and
tasks are solvable by construction (target = random op-walk from start).

G5 UNIVERSALITY: does the co-policy learned on human domains still beat plain
search on machine-made worlds? ADVERSARIAL TURN: search world-space for the
world that maximally breaks the policy; then SELF-REPAIR at the impasse — the
engine re-learns a policy for the failure world on its own (stuck -> invent).

LAWMAKER (G6): each world is one data point — structure features (invertible
fraction, branching, dimension) vs outcomes (policy advantage). Fit a law on
worlds inside a parameter range, then FORGE OUT-OF-RANGE WORLDS to test
EXTRAPOLATION. Interpolation is curve-fitting; surviving extrapolation is what
makes a law a law.
"""
from __future__ import annotations

import math
import random
from typing import Callable, Dict, List, Optional, Tuple

from . import invariants
from .adjoint import co_policies, solve_with_policy
from .icgg.core import Grammar, Operation, SearchEngine

BOUND = 48
_TRANSFERRED_POLICY = {"schema": "regress_adaptive", "phi": 0.0, "R": 2}


# ── forged world ──────────────────────────────────────────────────────────────
class ForgedWorld:
    """A machine-made reasoning domain over int-tuple states."""

    def __init__(self, seed: int, dim: int = 2, n_invertible: int = 4,
                 n_oneway: int = 2):
        self.seed = seed
        self.dim = dim
        self.name = f"forged_{seed}_d{dim}_i{n_invertible}_o{n_oneway}"
        rng = random.Random(seed)
        self._ops: List[Tuple[str, Callable, Optional[Callable]]] = []

        # Invertible generator pairs (op, inverse) — by construction.
        kinds = ["addv", "scale", "swap", "reflect"]
        for i in range(n_invertible):
            kind = rng.choice(kinds)
            if kind == "addv":
                v = tuple(rng.choice([-3, -2, -1, 1, 2, 3]) for _ in range(dim))
                self._ops.append((f"add{i}", self._mk_add(v), self._mk_add(tuple(-x for x in v))))
            elif kind == "scale":
                c = rng.randrange(dim)
                self._ops.append((f"dbl{i}_{c}", self._mk_dbl(c), self._mk_half(c)))
            elif kind == "swap" and dim >= 2:
                a, b = rng.sample(range(dim), 2)
                f = self._mk_swap(a, b)
                self._ops.append((f"swp{i}_{a}{b}", f, f))  # self-inverse
            else:
                c = rng.randrange(dim)
                f = self._mk_reflect(c)
                self._ops.append((f"ref{i}_{c}", f, f))  # self-inverse

        # One-way ops (no usable inverse) — realism / difficulty.
        for i in range(n_oneway):
            c = rng.randrange(dim)
            self._ops.append((f"crush{i}_{c}", self._mk_crush(c), None))

        self.frac_invertible = n_invertible / max(1, (n_invertible + n_oneway))

    # op factories (bounded, total-or-None)
    @staticmethod
    def _mk_add(v):
        def f(s):
            t = tuple(x + y for x, y in zip(s, v))
            return t if all(0 <= x <= BOUND for x in t) else None
        return f

    @staticmethod
    def _mk_dbl(c):
        def f(s):
            t = list(s); t[c] = t[c] * 2
            return tuple(t) if t[c] <= BOUND else None
        return f

    @staticmethod
    def _mk_half(c):
        def f(s):
            if s[c] % 2 != 0:
                return None
            t = list(s); t[c] = t[c] // 2
            return tuple(t)
        return f

    @staticmethod
    def _mk_swap(a, b):
        def f(s):
            t = list(s); t[a], t[b] = t[b], t[a]
            return tuple(t)
        return f

    @staticmethod
    def _mk_reflect(c):
        def f(s):
            t = list(s); t[c] = BOUND - t[c]
            return tuple(t)
        return f

    @staticmethod
    def _mk_crush(c):
        def f(s):
            t = list(s); t[c] = t[c] // 3
            return tuple(t) if tuple(t) != s else None
        return f

    # Domain protocol
    def base_grammar(self) -> Grammar:
        g = Grammar()
        for name, f, _inv in self._ops:
            g.add(Operation(name, f))
        return g

    def tasks(self, n: int, seed: int, split: str) -> List[Tuple[tuple, tuple]]:
        rng = random.Random((self.seed << 8) ^ seed ^ (0 if split == "train" else 1))
        g = self.base_grammar()
        out = []
        walk_lo, walk_hi = (4, 8) if split == "train" else (6, 10)
        tries = 0
        while len(out) < n and tries < n * 30:
            tries += 1
            start = tuple(rng.randint(4, BOUND - 4) for _ in range(self.dim))
            cur = start
            for _ in range(rng.randint(walk_lo, walk_hi)):
                nxt = g.next_states(cur)
                if not nxt:
                    break
                cur = rng.choice(nxt)[1]
            if cur != start:
                out.append((start, cur))
        return out

    def gain(self, states) -> float:
        if not states:
            return 0.0
        a, b = states[0], states[-1]
        return float(sum(abs(x - y) for x, y in zip(a, b)))


class ForgedAdapter:
    """Goal-structure adapter DERIVED automatically from the world's generators."""

    def __init__(self, world: ForgedWorld):
        self.world = world

    def distance(self, S, T) -> float:
        return float(sum(abs(x - y) for x, y in zip(S, T)))

    def interpolate(self, S, T, phi: float):
        M = tuple(int(round(s + (t - s) * phi)) for s, t in zip(S, T))
        return M if M not in (S, T) else None

    def project(self, S, T):
        P = (T[0],) + tuple(S[1:])
        return P if P not in (S, T) else None

    def regress(self, T):
        """Candidate (T', final_op) pairs via constructed inverses, verified:
        op(T') must equal T. Ordered by distance reduction potential."""
        out = []
        for name, f, inv in self.world._ops:
            if inv is None:
                continue
            Tp = inv(T)
            if Tp is None or Tp == T:
                continue
            if f(Tp) == T:  # verified pullback
                out.append((Tp, name))
        return out


# ── G5: universality + adversarial turn + self-repair at impasse ─────────────
def _mean_solve(world: ForgedWorld, adapter, policy, seeds: List[int],
                n: int = 10) -> dict:
    g = world.base_grammar()
    eng = SearchEngine(g)
    b_tot = p_tot = 0
    b_ok = p_ok = cnt = 0
    for s in seeds:
        for S, T in world.tasks(n, seed=s, split="test"):
            r = eng.solve(S, T)
            b_tot += r.expanded; b_ok += r.success; cnt += 1
            ok, exp, _ = solve_with_policy(world, adapter, S, T, policy)
            p_tot += exp; p_ok += ok
    cnt = max(1, cnt)
    return {"base_expanded": b_tot / cnt, "base_sr": b_ok / cnt,
            "policy_expanded": p_tot / cnt, "policy_sr": p_ok / cnt,
            "advantage": (b_tot / cnt) / max(1e-9, p_tot / cnt)}


def _learn_policy_on_world(world: ForgedWorld, adapter, seeds: List[int]) -> Optional[dict]:
    """Self-repair at impasse: the engine re-selects a policy FOR THIS WORLD
    on its train split — no human in the loop."""
    g = world.base_grammar()
    eng = SearchEngine(g)
    base_tot = base_ok = cnt = 0
    for s in seeds:
        for S, T in world.tasks(8, seed=s, split="train"):
            r = eng.solve(S, T); base_tot += r.expanded; base_ok += r.success; cnt += 1
    cnt = max(1, cnt)
    best = None
    for p in co_policies():
        tot = ok = 0
        for s in seeds:
            for S, T in world.tasks(8, seed=s, split="train"):
                o, e, _ = solve_with_policy(world, adapter, S, T, p)
                tot += e; ok += o
        if ok / cnt < base_ok / cnt - 1e-9:
            continue
        if best is None or tot < best[1]:
            best = (p, tot)
    return best[0] if best else None


def universality(n_worlds: int = 16, seeds: int = 2, seed0: int = 5000,
                 policy: dict | None = None) -> dict:
    seed_list = list(range(seeds))
    rng = random.Random(seed0)
    pol = policy or _TRANSFERRED_POLICY
    rows, wins = [], 0
    for i in range(n_worlds):
        w = ForgedWorld(seed=seed0 + i, dim=rng.choice((2, 3)),
                        n_invertible=rng.randint(3, 5), n_oneway=rng.randint(1, 3))
        r = _mean_solve(w, ForgedAdapter(w), pol, seed_list)
        win = r["policy_expanded"] < r["base_expanded"] and r["policy_sr"] >= r["base_sr"] - 1e-9
        wins += win
        rows.append({"world": w.name, "frac_invertible": round(w.frac_invertible, 2),
                     **{k: round(v, 2) for k, v in r.items()}, "win": win})
    return {"n_worlds": n_worlds, "wins": wins, "win_rate": round(wins / n_worlds, 2),
            "policy": pol, "g5_universality_pass": wins / n_worlds >= 0.7, "rows": rows}


def adversarial(n_probe: int = 14, seeds: int = 2, seed0: int = 9000) -> dict:
    """Search world-space for the policy's worst world; then self-repair."""
    seed_list = list(range(seeds))
    rng = random.Random(seed0)
    worst = None
    for i in range(n_probe):
        w = ForgedWorld(seed=seed0 + i, dim=rng.choice((2, 3)),
                        n_invertible=rng.randint(1, 5), n_oneway=rng.randint(1, 4))
        r = _mean_solve(w, ForgedAdapter(w), _TRANSFERRED_POLICY, seed_list)
        badness = (1.0 - r["policy_sr"]) * 1000 + r["policy_expanded"] / max(1.0, r["base_expanded"])
        if worst is None or badness > worst["badness"]:
            worst = {"world": w, "stats": r, "badness": badness}

    w = worst["world"]; stats = worst["stats"]
    counterexample = stats["policy_expanded"] >= stats["base_expanded"] or stats["policy_sr"] < stats["base_sr"]
    out = {"worst_world": w.name,
           "frac_invertible": round(w.frac_invertible, 2),
           "stats": {k: round(v, 2) for k, v in stats.items()},
           "counterexample_found": bool(counterexample)}

    # SELF-REPAIR AT IMPASSE: stuck -> the engine invents/selects a new method
    # for this world on its own, then re-measures on held-out tasks.
    repaired_policy = _learn_policy_on_world(w, ForgedAdapter(w), seed_list)
    if repaired_policy:
        r2 = _mean_solve(w, ForgedAdapter(w), repaired_policy, seed_list)
        out["self_repair"] = {
            "policy": repaired_policy,
            "after": {k: round(v, 2) for k, v in r2.items()},
            "repaired": r2["policy_expanded"] < stats["policy_expanded"]
                        or r2["policy_sr"] > stats["policy_sr"],
        }
    else:
        out["self_repair"] = {"policy": None, "repaired": False}
    return out


# ── G6: the Lawmaker — laws across universes, tested by extrapolation ────────
def lawmaker(n_train_worlds: int = 14, seeds: int = 2) -> dict:
    """Law: relation between a world-structure feature and policy advantage.
    Fit on worlds with frac_invertible in the MID range; test by forging worlds
    OUTSIDE that range (extrapolation)."""
    seed_list = list(range(seeds))

    def measure(worlds):
        feats, outs = [], []
        for w in worlds:
            r = _mean_solve(w, ForgedAdapter(w), _TRANSFERRED_POLICY, seed_list)
            feats.append(w.frac_invertible)
            outs.append(math.log(max(1e-9, r["advantage"])))
        return feats, outs

    # TRAIN band: frac_invertible ~ 0.4..0.67
    train_worlds = []
    i = 0
    while len(train_worlds) < n_train_worlds and i < 200:
        w = ForgedWorld(seed=20000 + i, dim=2 + (i % 2),
                        n_invertible=random.Random(i).randint(2, 4),
                        n_oneway=random.Random(i ^ 7).randint(2, 3))
        if 0.35 <= w.frac_invertible <= 0.68:
            train_worlds.append(w)
        i += 1
    f_tr, o_tr = measure(train_worlds)
    rho_train = invariants.spearman(f_tr, o_tr)

    # EXTRAPOLATION band: very low (<0.3) and very high (>0.75) invertibility
    extra_worlds = []
    i = 0
    while len(extra_worlds) < 10 and i < 300:
        rr = random.Random(31000 + i)
        w = ForgedWorld(seed=31000 + i, dim=rr.choice((2, 3)),
                        n_invertible=rr.choice((1, 5, 6)),
                        n_oneway=rr.choice((1, 4, 5)))
        if w.frac_invertible < 0.30 or w.frac_invertible > 0.75:
            extra_worlds.append(w)
        i += 1
    f_ex, o_ex = measure(extra_worlds)
    rho_extra = invariants.spearman(f_ex, o_ex)

    same_sign = (rho_train > 0) == (rho_extra > 0)
    g6 = abs(rho_extra) >= 0.5 and same_sign
    return {
        "law": "goal-regression advantage increases with the world's invertible-operator fraction",
        "train_band": "frac_invertible in [0.35, 0.68]",
        "rho_train": round(rho_train, 3),
        "n_train_worlds": len(train_worlds),
        "extrapolation_band": "frac_invertible < 0.30 or > 0.75",
        "rho_extrapolation": round(rho_extra, 3),
        "n_extra_worlds": len(extra_worlds),
        "g6_law_survives_extrapolation": bool(g6),
        "verdict": ("LAW (survives extrapolation)" if g6
                    else "curve-fit only (did not survive extrapolation)"),
    }
