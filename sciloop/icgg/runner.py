"""ICGG runner — generational grammar growth + cross-family transfer.

run_growth: solve TRAIN -> mine -> certify -> add certified macros -> repeat
for G generations, then evaluate on held-out TEST (before vs after).

transfer_matrix: certify macros on family A, measure their held-out effect on
family B (are trace-derived abstractions family-specific or transferable?).
"""
from __future__ import annotations

from typing import Dict, List

from . import certify as certmod
from .core import Grammar, SearchEngine
from .domains import Domain, get_domain
from .miner import mine


def _solve_train(grammar: Grammar, domain: Domain, seed: int, n: int,
                 max_depth: int, max_expanded: int):
    engine = SearchEngine(grammar, max_depth=max_depth, max_expanded=max_expanded)
    runs = []
    for start, target in domain.tasks(n, seed=seed, split="train"):
        r = engine.solve(start, target)
        if r.success:
            runs.append(r)
    return runs


def _eval(grammar: Grammar, domain: Domain, seeds: List[int], n: int,
          max_depth: int, max_expanded: int) -> Dict[str, float]:
    total, solved, count = 0, 0, 0
    for seed in seeds:
        engine = SearchEngine(grammar, max_depth=max_depth, max_expanded=max_expanded)
        for start, target in domain.tasks(n, seed=seed, split="test"):
            r = engine.solve(start, target)
            total += r.expanded
            solved += 1 if r.success else 0
            count += 1
    count = max(1, count)
    return {"mean_expanded": total / count, "solve_rate": solved / count}


def run_growth(domain_name: str, generations: int = 2, seeds: int = 3,
               n_train: int = 30, n_test: int = 25,
               max_depth: int = 14, max_expanded: int = 20000) -> dict:
    domain = get_domain(domain_name)
    seed_list = list(range(seeds))

    grammar = domain.base_grammar()
    before = _eval(grammar, domain, seed_list, n_test, max_depth, max_expanded)

    generations_log = []
    certified_all: List[dict] = []

    for gen in range(generations):
        # gather successful training traces across seeds with the current grammar
        train_runs = []
        for s in seed_list:
            train_runs += _solve_train(grammar, domain, s, n_train, max_depth, max_expanded)
        motifs = mine(train_runs, domain.gain, min_support=2, min_gain=1.0, max_len=3)
        certs = certmod.certify(domain, motifs, seed_list, n_test=n_test,
                                max_depth=max_depth, max_expanded=max_expanded, cap=8)
        kept = [c for c in certs if c.kept and c.name not in grammar.ops]
        for c in kept:
            grammar.add_macro(c.name, c.sequence)
        generations_log.append({
            "generation": gen,
            "train_successes": len(train_runs),
            "motifs_mined": len(motifs),
            "certifications": [c.to_dict() for c in certs],
            "kept": [c.name for c in kept],
        })
        certified_all += [c.to_dict() for c in kept]
        if not kept:
            break  # nothing new certified -> converged

    after = _eval(grammar, domain, seed_list, n_test, max_depth, max_expanded)

    return {
        "domain": domain_name,
        "seeds": seeds,
        "before": before,
        "after": after,
        "expanded_reduction": round(before["mean_expanded"] - after["mean_expanded"], 1),
        "certified_operators": certified_all,
        "final_grammar_size": len(grammar.ops),
        "generations": generations_log,
        "grammar": grammar,  # for reuse (transfer); not JSON-serialized by caller
    }


def transfer_matrix(domain_names: List[str], seeds: int = 3, n_test: int = 25,
                    max_depth: int = 14, max_expanded: int = 20000) -> dict:
    """Grow a grammar on each family, then measure its held-out effect on every
    family. Diagonal = within-family; off-diagonal = transfer."""
    grown: Dict[str, Grammar] = {}
    baselines: Dict[str, float] = {}
    seed_list = list(range(seeds))

    for name in domain_names:
        res = run_growth(name, generations=2, seeds=seeds, n_test=n_test,
                         max_depth=max_depth, max_expanded=max_expanded)
        grown[name] = res["grammar"]
        baselines[name] = res["before"]["mean_expanded"]

    matrix = {}
    for src in domain_names:
        matrix[src] = {}
        # extract just the macros grown on src
        src_macros = {n: op for n, op in grown[src].ops.items() if n.startswith("macro_")}
        for tgt in domain_names:
            dom = get_domain(tgt)
            g = dom.base_grammar()
            for n, op in src_macros.items():
                g.add(op)  # inject src-grown macro ops into tgt base grammar
            ev = _eval(g, dom, seed_list, n_test, max_depth, max_expanded)
            base_mean = baselines[tgt]
            reduction = base_mean - ev["mean_expanded"]
            matrix[src][tgt] = {
                "mean_expanded": round(ev["mean_expanded"], 1),
                "base_expanded": round(base_mean, 1),
                "reduction": round(reduction, 1),
            }
    return {"domains": domain_names, "matrix": matrix}
