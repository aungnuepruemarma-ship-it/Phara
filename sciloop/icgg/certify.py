"""Certification — a mined macro is KEPT only if it earns its place.

For each candidate macro we compare, on HELD-OUT (test) tasks across several
seeds, the mean nodes-expanded of:
  base                 — grammar with no macro
  +macro               — grammar + the mined macro
  +random_macro        — grammar + a random operator sequence of the same length
  +freq_macro          — grammar + the most frequent base op repeated to same length

A macro is certified iff (+macro) reduces mean expanded vs base AND beats both
control macros, robustly (mean over seeds). This defeats the demo's train==test
flaw and the "any macro shrinks depth" illusion.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Tuple

from .core import Grammar, SearchEngine
from .domains import Domain
from .miner import Motif


@dataclass
class Certification:
    name: str
    sequence: Tuple[str, ...]
    kept: bool
    base_expanded: float
    macro_expanded: float
    random_expanded: float
    freq_expanded: float
    improvement: float          # base - macro (positive = better)
    reason: str

    def to_dict(self) -> dict:
        return {
            "name": self.name, "sequence": list(self.sequence), "kept": self.kept,
            "base_expanded": round(self.base_expanded, 1),
            "macro_expanded": round(self.macro_expanded, 1),
            "random_expanded": round(self.random_expanded, 1),
            "freq_expanded": round(self.freq_expanded, 1),
            "improvement": round(self.improvement, 1), "reason": self.reason,
        }


def _mean_expanded(grammar: Grammar, tasks: List[Tuple[object, object]],
                   max_depth: int, max_expanded: int) -> Tuple[float, int]:
    engine = SearchEngine(grammar, max_depth=max_depth, max_expanded=max_expanded)
    total, solved = 0, 0
    for start, target in tasks:
        r = engine.solve(start, target)
        total += r.expanded
        solved += 1 if r.success else 0
    n = max(1, len(tasks))
    return total / n, solved


def _with_macro(base: Grammar, name: str, seq) -> Grammar:
    g = base.clone()
    g.add_macro(name, seq)
    return g


def certify(domain: Domain, motifs: List[Motif], seeds: List[int],
            n_test: int = 25, max_depth: int = 14, max_expanded: int = 20000,
            cap: int = 8) -> List[Certification]:
    base_ops = domain.base_grammar().names()
    results: List[Certification] = []
    rng = random.Random(1234)

    for motif in motifs[:cap]:
        seq = motif.sequence
        L = len(seq)
        base_scores, macro_scores, rand_scores, freq_scores = [], [], [], []

        for seed in seeds:
            tasks = domain.tasks(n_test, seed=seed, split="test")
            base = domain.base_grammar()
            rand_seq = tuple(rng.choice(base_ops) for _ in range(L))
            # frequency control: most common op in this motif's alphabet, repeated
            freq_seq = tuple([max(set(seq), key=seq.count)] * L)

            b, _ = _mean_expanded(base, tasks, max_depth, max_expanded)
            m, _ = _mean_expanded(_with_macro(base, motif.name, seq), tasks, max_depth, max_expanded)
            r, _ = _mean_expanded(_with_macro(base, "rand", rand_seq), tasks, max_depth, max_expanded)
            f, _ = _mean_expanded(_with_macro(base, "freq", freq_seq), tasks, max_depth, max_expanded)
            base_scores.append(b); macro_scores.append(m)
            rand_scores.append(r); freq_scores.append(f)

        bm = sum(base_scores) / len(base_scores)
        mm = sum(macro_scores) / len(macro_scores)
        rm = sum(rand_scores) / len(rand_scores)
        fm = sum(freq_scores) / len(freq_scores)
        improvement = bm - mm

        beats_base = mm < bm - 1e-9
        beats_random = mm < rm - 1e-9
        beats_freq = mm < fm - 1e-9
        kept = beats_base and beats_random and beats_freq

        if kept:
            reason = "certified: beats base + random + frequency controls on held-out tasks"
        elif not beats_base:
            reason = "rejected: no improvement over base grammar"
        elif not beats_random:
            reason = "rejected: does not beat a random macro of equal length"
        else:
            reason = "rejected: does not beat a frequency-only macro"

        results.append(Certification(
            name=motif.name, sequence=seq, kept=kept,
            base_expanded=bm, macro_expanded=mm, random_expanded=rm,
            freq_expanded=fm, improvement=improvement, reason=reason,
        ))
    return results
