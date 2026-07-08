"""Structural evolution — biology at the level of mind design.

A population of Frames evolves by STRUCTURAL variation (swap reasoning policy,
add/drop certified macros, crossover) under multi-domain fitness. No weights,
no gradients — the *architecture of reasoning* is the genotype. Meta-traces of
(mutation -> fitness change) are recorded so reflect.py can mine rules about
how minds improve (self-improvement of self-improvement).

Discipline: evolution selects on the TRAIN split; the G2 verdict (evolved vs
hand-built) is read on held-out TEST tasks only.
"""
from __future__ import annotations

import random
from typing import Callable, List

from . import frames
from .adjoint import co_policies

MUTATIONS = ["flip_macro", "swap_policy", "swap_policy_domain", "tweak_policy"]


def _mutate(frame: dict, rng: random.Random,
            bias: Callable[[random.Random], str] | None = None) -> tuple[dict, str]:
    pol = frame["policy_idx"]
    pol = dict(pol) if isinstance(pol, dict) else {d: pol for d in frames.DOMAINS}
    child = {
        "id": f"f{rng.randrange(10**6)}",
        "macro_mask": {d: list(m) for d, m in frame["macro_mask"].items()},
        "policy_idx": pol,
        "attends": list(frame["attends"]),
        "lineage": frame["lineage"][-3:] + [frame["id"]],
    }
    kind = bias(rng) if bias else rng.choice(MUTATIONS)
    n_pol = len(co_policies())
    if kind == "flip_macro":
        d = rng.choice(frames.DOMAINS)
        if child["macro_mask"][d]:
            i = rng.randrange(len(child["macro_mask"][d]))
            child["macro_mask"][d][i] ^= 1
    elif kind == "swap_policy":  # global move: one policy for all domains
        g = rng.randrange(n_pol)
        child["policy_idx"] = {d: g for d in frames.DOMAINS}
    elif kind == "swap_policy_domain":  # specialize ONE domain's policy
        d = rng.choice(frames.DOMAINS)
        child["policy_idx"][d] = rng.randrange(n_pol)
    elif kind == "tweak_policy":
        d = rng.choice(frames.DOMAINS)
        child["policy_idx"][d] = (child["policy_idx"][d] + rng.choice((-1, 1))) % n_pol
    return child, kind


def _crossover(a: dict, b: dict, rng: random.Random) -> dict:
    bp = b["policy_idx"]
    bp = dict(bp) if isinstance(bp, dict) else {d: bp for d in frames.DOMAINS}
    return {
        "id": f"x{rng.randrange(10**6)}",
        "macro_mask": {d: list(a["macro_mask"][d]) for d in frames.DOMAINS},
        "policy_idx": dict(bp),
        "attends": list(a["attends"]),
        "lineage": [a["id"], b["id"]],
    }


def evolve(pop_size: int = 8, generations: int = 6, seeds: int = 3,
           rng_seed: int = 1, bias: Callable[[random.Random], str] | None = None,
           crossover_rate: float = 0.25, printer=None) -> dict:
    def _p(msg):
        if printer:
            printer(msg)

    rng = random.Random(rng_seed)
    seed_list = list(range(seeds))

    pop = [frames.random_frame(rng, f"g0_{i}") for i in range(pop_size - 1)]
    pop.append(frames.default_frame())  # the hand-built mind competes too

    def score(fr):
        return frames.fitness(fr, seed_list, split="train")["overall"]

    scored = [(fr, score(fr)) for fr in pop]
    meta_traces: List[dict] = []
    history = []

    for gen in range(generations):
        scored.sort(key=lambda t: -t[1])
        best_fr, best_fit = scored[0]
        mean_fit = sum(s for _, s in scored) / len(scored)
        history.append({"generation": gen, "best": round(best_fit, 4),
                        "mean": round(mean_fit, 4),
                        "best_desc": frames.describe(best_fr)})
        _p(f"  gen {gen}: best={best_fit:.4f} mean={mean_fit:.4f}  [{frames.describe(best_fr)}]")

        next_pop = [scored[0]]  # elitism
        while len(next_pop) < pop_size:
            # tournament selection
            def pick():
                cands = rng.sample(scored, min(3, len(scored)))
                return max(cands, key=lambda t: t[1])
            pa, fa = pick()
            if rng.random() < crossover_rate:
                pb, _ = pick()
                child = _crossover(pa, pb, rng)
                kind = "crossover"
            else:
                child, kind = _mutate(pa, rng, bias=bias)
            fc = score(child)
            meta_traces.append({"parent_fitness": fa, "mutation": kind,
                                "child_fitness": fc, "delta": round(fc - fa, 4),
                                "generation": gen})
            next_pop.append((child, fc))
        scored = next_pop

    scored.sort(key=lambda t: -t[1])
    best_fr, best_train_fit = scored[0]

    # G2 verdict on HELD-OUT tasks: evolved best vs the hand-built frame.
    hand = frames.default_frame()
    evolved_test = frames.fitness(best_fr, seed_list, split="test")
    hand_test = frames.fitness(hand, seed_list, split="test")

    return {
        "history": history,
        "meta_traces": meta_traces,
        "best_frame": best_fr,
        "best_desc": frames.describe(best_fr),
        "evolved_test_fitness": evolved_test,
        "hand_built_test_fitness": hand_test,
        "evolution_beats_design": evolved_test["overall"] > hand_test["overall"] + 1e-9,
    }
