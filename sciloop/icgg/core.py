"""Grammar, Operations, and a search engine that accounts for nodes expanded.

State is a hashable value (domain-defined). An Operation maps State -> State|None.
Macros are named operator sequences promoted from mined motifs.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Dict, Hashable, List, Optional, Sequence, Tuple

State = Hashable
Trace = List[str]


@dataclass(frozen=True)
class Operation:
    name: str
    func: Callable[[State], Optional[State]]

    def apply(self, x: State) -> Optional[State]:
        try:
            return self.func(x)
        except Exception:
            return None


@dataclass
class Grammar:
    ops: Dict[str, Operation] = field(default_factory=dict)

    def add(self, op: Operation) -> None:
        self.ops[op.name] = op

    def names(self) -> List[str]:
        return list(self.ops.keys())

    def next_states(self, x: State) -> List[Tuple[str, State]]:
        out = []
        for name, op in self.ops.items():
            y = op.apply(x)
            if y is not None and y != x:
                out.append((name, y))
        return out

    def add_macro(self, name: str, sequence: Sequence[str]) -> None:
        seq = tuple(sequence)
        base = dict(self.ops)  # snapshot so the macro isn't self-referential

        def _macro(x: State) -> Optional[State]:
            cur = x
            for step in seq:
                op = base.get(step)
                if op is None:
                    return None
                cur = op.apply(cur)
                if cur is None:
                    return None
            return cur

        self.add(Operation(name=name, func=_macro))

    def clone(self) -> "Grammar":
        return Grammar(ops=dict(self.ops))


@dataclass
class SolveResult:
    success: bool
    trace: Trace
    states: List[State]
    expanded: int          # the honest cost — nodes popped/expanded
    depth: int

    def to_dict(self) -> dict:
        return {"success": self.success, "trace": self.trace,
                "states": list(self.states), "expanded": self.expanded, "depth": self.depth}


class SearchEngine:
    """Breadth-first search that counts nodes expanded (the true effort metric)."""

    def __init__(self, grammar: Grammar, max_depth: int = 14, max_expanded: int = 20000):
        self.grammar = grammar
        self.max_depth = max_depth
        self.max_expanded = max_expanded

    def solve(self, start: State, target: State) -> SolveResult:
        if start == target:
            return SolveResult(True, [], [start], 0, 0)
        q = deque([(start, [], [start])])
        seen = {start}
        expanded = 0
        while q and expanded < self.max_expanded:
            x, trace, states = q.popleft()
            if len(trace) >= self.max_depth:
                continue
            expanded += 1
            for opname, y in self.grammar.next_states(x):
                if y in seen:
                    continue
                seen.add(y)
                nt, ns = trace + [opname], states + [y]
                if y == target:
                    return SolveResult(True, nt, ns, expanded, len(nt))
                q.append((y, nt, ns))
        return SolveResult(False, [], [start], expanded, -1)
