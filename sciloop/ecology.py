"""Operator Ecology v1 — a fitness ledger over certified operators.

Operators earn fitness from wins (search-effort reductions) net of cost. Weak
operators are retired. This is the substrate for later merge/split/compete
dynamics (Phase 4), kept minimal and evidence-driven here.
"""
from __future__ import annotations

from .evidence import Store


def register_certified(store: Store, domain: str, certifications: list[dict],
                       evidence_id: str | None = None) -> list[str]:
    """Add newly-certified ICGG operators to the ecology ledger."""
    added = []
    for c in certifications:
        if not c.get("kept"):
            continue
        store.add_operator(c["name"], domain, c.get("sequence", []), evidence_id=evidence_id)
        # seed fitness from the certified improvement (win + cost = seq length)
        store.record_operator_use(c["name"], win=True, cost=float(len(c.get("sequence", []))))
        added.append(c["name"])
    return added


def prune(store: Store, min_uses: int = 5, min_fitness: float = 0.3) -> list[str]:
    return store.retire_weak_operators(min_uses=min_uses, min_fitness=min_fitness)


def summary(store: Store) -> dict:
    ops = store.operators()
    certified = [o for o in ops if o["status"] == "certified"]
    return {
        "total": len(ops),
        "certified": len(certified),
        "retired": len([o for o in ops if o["status"] == "retired"]),
        "top": [{"name": o["name"], "domain": o["domain"], "fitness": round(o["fitness"], 3),
                 "uses": o["uses"], "wins": o["wins"]} for o in certified[:10]],
    }
