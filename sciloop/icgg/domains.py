"""Task families for ICGG. Each Domain provides ops + seeded TRAIN/TEST tasks.

Three structurally different families let us test cross-family transfer:
  arith   — integers, reach target by +1/-1/*2//2/*3
  strings — reach a target string via append/drop/reverse/swap
  vector  — reach a target (x,y) on a lattice via unit moves + jumps
"""
from __future__ import annotations

import random
from typing import Callable, List, Tuple

from .core import Grammar, Operation


class Domain:
    name = "base"

    def base_grammar(self) -> Grammar:
        raise NotImplementedError

    def tasks(self, n: int, seed: int, split: str) -> List[Tuple[object, object]]:
        """Return (start, target) pairs. split in {'train','test'} disjoint by seed."""
        raise NotImplementedError

    def gain(self, states: List[object]) -> float:
        """Progress metric for a successful run (bigger = more useful motif)."""
        return float(len(states))


# ── arith ────────────────────────────────────────────────────────────────────
class ArithDomain(Domain):
    name = "arith"

    def base_grammar(self) -> Grammar:
        g = Grammar()
        g.add(Operation("add1", lambda x: x + 1))
        g.add(Operation("sub1", lambda x: x - 1 if x > 0 else None))
        g.add(Operation("double", lambda x: x * 2 if x < 10**9 else None))
        g.add(Operation("halve", lambda x: x // 2 if x % 2 == 0 and x > 0 else None))
        g.add(Operation("triple", lambda x: x * 3 if x < 10**9 else None))
        return g

    def tasks(self, n: int, seed: int, split: str) -> List[Tuple[int, int]]:
        rng = random.Random((seed << 1) ^ (0 if split == "train" else 1))
        out = []
        for _ in range(n):
            # Targets that reward double/add1 style macros.
            k = rng.randint(3, 9)
            t = (1 << k) - rng.choice([0, 1])
            out.append((1, t))
        return out

    def gain(self, states: List[int]) -> float:
        return float(states[-1] - states[0]) if states else 0.0


# ── strings ──────────────────────────────────────────────────────────────────
class StringDomain(Domain):
    name = "strings"
    _AB = "ab"

    def base_grammar(self) -> Grammar:
        g = Grammar()
        g.add(Operation("app_a", lambda s: s + "a" if len(s) < 12 else None))
        g.add(Operation("app_b", lambda s: s + "b" if len(s) < 12 else None))
        g.add(Operation("drop", lambda s: s[:-1] if s else None))
        g.add(Operation("rev", lambda s: s[::-1] if len(s) > 1 else None))
        g.add(Operation("dup", lambda s: s + s if 0 < len(s) <= 6 else None))
        return g

    def tasks(self, n: int, seed: int, split: str) -> List[Tuple[str, str]]:
        rng = random.Random((seed << 1) ^ (2 if split == "train" else 3))
        out = []
        for _ in range(n):
            L = rng.randint(3, 8)
            t = "".join(rng.choice(self._AB) for _ in range(L))
            out.append(("", t))
        return out

    def gain(self, states: List[str]) -> float:
        return float(len(states[-1])) if states else 0.0


# ── vector ───────────────────────────────────────────────────────────────────
class VectorDomain(Domain):
    name = "vector"

    def base_grammar(self) -> Grammar:
        g = Grammar()
        g.add(Operation("up", lambda p: (p[0], p[1] + 1) if p[1] < 40 else None))
        g.add(Operation("right", lambda p: (p[0] + 1, p[1]) if p[0] < 40 else None))
        g.add(Operation("down", lambda p: (p[0], p[1] - 1) if p[1] > 0 else None))
        g.add(Operation("left", lambda p: (p[0] - 1, p[1]) if p[0] > 0 else None))
        g.add(Operation("jump_r", lambda p: (p[0] + 3, p[1]) if p[0] + 3 <= 40 else None))
        g.add(Operation("jump_u", lambda p: (p[0], p[1] + 3) if p[1] + 3 <= 40 else None))
        return g

    def tasks(self, n: int, seed: int, split: str) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        rng = random.Random((seed << 1) ^ (4 if split == "train" else 5))
        out = []
        for _ in range(n):
            t = (rng.randint(6, 18), rng.randint(6, 18))
            out.append(((0, 0), t))
        return out

    def gain(self, states: List[Tuple[int, int]]) -> float:
        if not states:
            return 0.0
        a, b = states[0], states[-1]
        return float(abs(b[0] - a[0]) + abs(b[1] - a[1]))


DOMAINS = {d.name: d for d in (ArithDomain(), StringDomain(), VectorDomain())}


def get_domain(name: str) -> Domain:
    if name not in DOMAINS:
        raise ValueError(f"Unknown domain {name!r}. Available: {list(DOMAINS)}")
    return DOMAINS[name]
