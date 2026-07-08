"""Self-reflection — the engine's own improvement process becomes a domain.

Meta-traces from evolution ((mutation -> fitness delta) sequences along
lineages) are mined with the SAME machinery used on object-level problems
(icgg.miner.mine) to discover META-OPERATORS: mutation kinds/motifs that
reliably improve minds. A kept meta-operator biases the mutation schedule of
the next evolution run; the G3 test asks whether that bias beats a uniform
random schedule on a fresh run (paired seeds).

introspect() renders the engine's self-report, and every claim must resolve to
an evidence id (G4 is a mechanical check, not an aspiration).
"""
from __future__ import annotations

import json
import random
from typing import List

from . import evolution, genome
from .evidence import Store
from .icgg.miner import mine


class _MetaRun:
    """Adapter: a lineage of mutations as a SolveResult-shaped trace."""
    def __init__(self, mutations: List[str], fitnesses: List[float]):
        self.success = fitnesses[-1] > fitnesses[0]
        self.trace = mutations
        self.states = fitnesses
        self.expanded = len(mutations)
        self.depth = len(mutations)


def mine_meta_operators(meta_traces: List[dict]) -> List[dict]:
    """Group per-generation improving chains and mine mutation motifs that
    correlate with fitness gain."""
    # Build chains: consecutive meta-trace entries within a generation.
    runs: List[_MetaRun] = []
    by_gen: dict = {}
    for t in meta_traces:
        by_gen.setdefault(t["generation"], []).append(t)
    for gen, items in by_gen.items():
        muts = [t["mutation"] for t in items]
        fits = [items[0]["parent_fitness"]] + [t["child_fitness"] for t in items]
        if len(muts) >= 2:
            runs.append(_MetaRun(muts, fits))

    successful = [r for r in runs if r.success]
    motifs = mine(successful, gain_fn=lambda states: (states[-1] - states[0]) * 100.0,
                  min_support=2, min_gain=0.0, max_len=2)
    out = []
    for m in motifs[:5]:
        out.append({"motif": list(m.sequence), "support": m.support,
                    "avg_fitness_gain_x100": round(m.avg_gain, 3)})
    # Also: single-mutation expected delta (the simplest meta-knowledge).
    agg: dict = {}
    for t in meta_traces:
        agg.setdefault(t["mutation"], []).append(t["delta"])
    singles = [{"mutation": k, "mean_delta": round(sum(v) / len(v), 4), "n": len(v)}
               for k, v in agg.items()]
    singles.sort(key=lambda s: -s["mean_delta"])
    return out + [{"singles": singles}]


def bias_from(meta_ops: List[dict]):
    """Turn mined meta-operators into a biased schedule: 3x weight on favored
    mutation kinds AND a modulated crossover rate (the fix: 'crossover' is a
    reproduction choice, not a mutation kind, so it biases the rate)."""
    favored: set = set()
    for m in meta_ops:
        if "motif" in m:
            favored.update(m["motif"])
        if "singles" in m:
            favored.update(s["mutation"] for s in m["singles"] if s["mean_delta"] > 0)
    crossover_rate = 0.5 if "crossover" in favored else 0.25
    favored &= set(evolution.MUTATIONS)
    if not favored and crossover_rate == 0.25:
        return None, 0.25
    weighted = (list(evolution.MUTATIONS) + list(favored) * 2) or list(evolution.MUTATIONS)

    def _bias(rng: random.Random) -> str:
        return rng.choice(weighted)
    return _bias, crossover_rate


def g3_test(meta_ops: List[dict], seeds: int = 3, generations: int = 4,
            pop: int = 6) -> dict:
    """Paired comparison on FRESH rng seeds: biased schedule vs uniform."""
    bias, xrate = bias_from(meta_ops)
    if bias is None and xrate == 0.25:
        return {"verdict": "no meta-operator to test", "pairs": []}
    pairs = []
    for rs in (101, 202, 303):
        b = evolution.evolve(pop_size=pop, generations=generations, seeds=seeds,
                             rng_seed=rs, bias=bias, crossover_rate=xrate)
        u = evolution.evolve(pop_size=pop, generations=generations, seeds=seeds,
                             rng_seed=rs, bias=None, crossover_rate=0.25)
        pairs.append({"rng_seed": rs,
                      "biased_final_best": b["history"][-1]["best"],
                      "uniform_final_best": u["history"][-1]["best"]})
    wins = sum(1 for p in pairs if p["biased_final_best"] > p["uniform_final_best"])
    ties = sum(1 for p in pairs if p["biased_final_best"] == p["uniform_final_best"])
    return {"pairs": pairs, "biased_wins": wins, "ties": ties,
            "verdict": ("meta-operator bias helps" if wins > len(pairs) / 2
                        else "no reliable acceleration (honest negative)")}


# ── grounded introspection (G4) ───────────────────────────────────────────────
def introspect() -> dict:
    store = Store()
    lines: List[str] = []
    all_resolve = True

    def claim(text: str, evidence_id: str | None):
        nonlocal all_resolve
        ok = bool(evidence_id and store.get_evidence(evidence_id))
        all_resolve &= ok
        lines.append(f"  {'✓' if ok else '✗'} {text}  [evidence {evidence_id or 'MISSING'}]")

    lines.append("SELF-REPORT — current mental framework (every claim cites evidence)")
    recs = genome.records()
    frames_r = [r for r in recs if r.get("kind") == "frame"]
    cons = [r for r in recs if r.get("kind") == "concept"]
    metas = [r for r in recs if r.get("kind") == "meta_operator"]
    ops = [r for r in recs if r.get("kind") in ("operator", "co_operator", "symmetry_operator")]

    lines.append(f"\nMy current best frame ({len(frames_r)} recorded):")
    for r in frames_r[-2:]:
        claim(f"frame '{r['name']}': {json.dumps(r['recipe'])[:120]}",
              (r.get("provenance") or [None])[0])
    lines.append(f"\nConcepts I invented ({len(cons)}):")
    for r in cons[-6:]:
        claim(f"{r['name']} — {r.get('notes','')[:100]}", (r.get("provenance") or [None])[0])
    lines.append(f"\nRules I learned about improving my own mind ({len(metas)}):")
    for r in metas[-4:]:
        claim(f"{r['name']} — {r.get('notes','')[:100]}", (r.get("provenance") or [None])[0])
    lines.append(f"\nOperators in my grammar ({len(ops)}):")
    for r in ops[-5:]:
        claim(f"{r['name']}", (r.get("provenance") or [None])[0])

    lines.append(f"\nG4 grounded-introspection check: "
                 f"{'PASS — every claim resolves to stored evidence' if all_resolve else 'FAIL'}")
    store.close()
    return {"report": "\n".join(lines), "g4_pass": all_resolve}
