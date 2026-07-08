"""Toolkit — tools and skills the engine's agents can actually CALL.

TOOLS are actions that produce evidence (fetch live data, run code in the
sandbox, run a grammar-growth or forge experiment, query stored knowledge).
SKILLS are the engine's own certified artifacts (co-operators, operators,
laws, concepts) exposed as invocable capabilities — the system's earned
repertoire, not a hardcoded library.

Agents request a tool with a single line:  TOOL: <name> {json args}
The runtime EXECUTES it (result -> evidence store) and returns the output to
the agent for a grounded follow-up. Talk is cheap; tool output is evidence.
"""
from __future__ import annotations

import json
from typing import Callable, Dict, Tuple

from . import genome


# ── tool implementations (each returns a short string result) ────────────────
def _t_live_fetch(args: dict) -> str:
    from . import livedata
    src = str(args.get("source", "weather"))
    fn = livedata.SOURCES.get(src)
    if not fn:
        return f"unknown source {src!r}; available: {list(livedata.SOURCES)}"
    d = fn()
    if not d:
        return f"{src}: UNAVAILABLE (network)"
    obs = livedata.series_observables(d["series"]) or {}
    return (f"{d['name']}: n={len(d['series'])} last={d['series'][-1]} "
            f"obs={json.dumps(obs)} src={d['url'][:80]}")


def _t_sandbox_run(args: dict) -> str:
    from . import sandbox
    code = str(args.get("code", ""))
    r = sandbox.run_code(code, timeout=int(args.get("timeout", 8)))
    out = (r.get("stdout") or "").strip() or (r.get("stderr") or "").strip()
    return f"exit={r['exit_code']} timed_out={r['timed_out']} output: {out[:500]}"


def _t_icgg_grow(args: dict) -> str:
    from .icgg import runner
    dom = str(args.get("domain", "arith"))
    res = runner.run_growth(dom, generations=1, seeds=2)
    kept = [c["name"] for c in res["certified_operators"]]
    return (f"{dom}: expanded {res['before']['mean_expanded']:.0f} -> "
            f"{res['after']['mean_expanded']:.0f}; certified={kept}")


def _t_forge_probe(args: dict) -> str:
    from . import worldforge
    seed = int(args.get("seed", 4242))
    w = worldforge.ForgedWorld(seed=seed, dim=int(args.get("dim", 2)))
    r = worldforge._mean_solve(w, worldforge.ForgedAdapter(w),
                               worldforge._TRANSFERRED_POLICY, [0], n=6)
    return (f"{w.name}: base={r['base_expanded']:.0f} policy={r['policy_expanded']:.0f} "
            f"advantage={r['advantage']:.2f} sr={r['policy_sr']:.2f}")


def _t_knowledge(args: dict) -> str:
    q = str(args.get("query", "")).lower()
    hits = [r for r in genome.records()
            if q in r.get("name", "").lower() or q in r.get("notes", "").lower()]
    if not hits:
        return f"no genome records matching {q!r}"
    return "; ".join(f"[{r['kind']}] {r['name']}: {r.get('notes','')[:80]}" for r in hits[:5])


TOOLS: Dict[str, Tuple[str, Callable[[dict], str]]] = {
    "live_fetch": ("fetch a real-time data series (source: weather|quakes|fx|wiki) "
                   "and return its cross-domain observables", _t_live_fetch),
    "sandbox_run": ("execute a short Python snippet in the isolated sandbox "
                    "(args: code, timeout)", _t_sandbox_run),
    "icgg_grow": ("run one generation of certified grammar growth on a domain "
                  "(args: domain=arith|strings|vector)", _t_icgg_grow),
    "forge_probe": ("synthesize one machine-made world and measure the current "
                    "policy on it (args: seed, dim)", _t_forge_probe),
    "knowledge": ("search the engine's genome (earned skills/laws/concepts) "
                  "(args: query)", _t_knowledge),
}


def skills() -> list[dict]:
    """The engine's EARNED repertoire, read from the genome."""
    out = []
    for r in genome.records():
        if r.get("kind") in ("co_operator", "operator", "symmetry_operator",
                             "concept", "law", "meta_operator", "frame"):
            out.append({"skill": r["name"], "kind": r["kind"],
                        "notes": (r.get("notes") or "")[:100]})
    return out


def call(name: str, args: dict) -> str:
    entry = TOOLS.get(name)
    if not entry:
        return f"unknown tool {name!r}; available: {list(TOOLS)}"
    try:
        return entry[1](args or {})
    except Exception as exc:  # tools must never crash the loop
        return f"tool {name} failed: {str(exc)[:200]}"


def catalog() -> str:
    lines = ["TOOLS:"]
    for n, (desc, _) in TOOLS.items():
        lines.append(f"  {n}: {desc}")
    sk = skills()
    lines.append(f"SKILLS (earned, from genome): {len(sk)}")
    for s in sk[:10]:
        lines.append(f"  [{s['kind']}] {s['skill']} — {s['notes']}")
    return "\n".join(lines)


def parse_tool_request(text: str) -> Tuple[str, dict] | None:
    """Find a 'TOOL: name {json}' line in an agent reply."""
    for line in (text or "").splitlines():
        line = line.strip()
        if line.upper().startswith("TOOL:"):
            body = line[5:].strip()
            parts = body.split(None, 1)
            if not parts:
                return None
            name = parts[0].strip()
            args = {}
            if len(parts) > 1:
                try:
                    args = json.loads(parts[1])
                except json.JSONDecodeError:
                    args = {}
            return name, args
    return None
