"""The Discovery Loop — the spine of SciLoop.

Hypothesis -> Execute -> Measure -> Falsify -> Compress -> Promote, over N cycles.
Verdicts are decided ONLY on executed_result / retrieved_source evidence; agent
claims are recorded but never sufficient. Falsified hypotheses are mutated for
the next cycle. Grammar growth (ICGG) runs as a computational experiment whose
certified operators are promoted into the ecology + genome — the concrete way
the runtime accumulates new primitives across runs.
"""
from __future__ import annotations

import json
import re

from . import agents, compiler, ecology, genome, geometry, invariants, llm
from .evidence import Store
from .icgg import runner as icgg_runner


def _p(printer, msg=""):
    if printer:
        printer(msg)


# ── experiment authoring ──────────────────────────────────────────────────────
_CODE_SYS = (
    "You are a computational scientist. Write a SHORT, self-contained Python 3 program "
    "(standard library only) that empirically tests the hypothesis via the given experiment "
    "idea. It MUST print clearly labeled results that let a reader judge support/refutation. "
    "Keep it under ~45 lines and fast (<5s). Respond with ONLY a ```python code block."
)


def _write_experiment(question: str, hypothesis: str, idea: str) -> str | None:
    text = llm.chat(
        [{"role": "system", "content": _CODE_SYS},
         {"role": "user", "content": f"Question: {question}\nHypothesis: {hypothesis}\n"
                                      f"Experiment idea: {idea}"}],
        temperature=0.3,
    )
    if not text:
        return None
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    code = (m.group(1) if m else text).strip()
    return code or None


# ── verdict judging ───────────────────────────────────────────────────────────
_JUDGE_SYS = (
    "You are a strict scientific referee. Given a hypothesis and ONLY the outputs of code that "
    "actually executed, decide the verdict. Ignore rhetoric; rely solely on the executed evidence. "
    'Respond with JSON: {"verdict": "supported|falsified|undecided", "reason": "..."}'
)


def _judge(hypothesis: str, executed_outputs: list[str]) -> tuple[str, str]:
    if not executed_outputs:
        return "undecided", "no executed evidence"
    ev = "\n\n".join(f"[experiment {i+1} output]:\n{o[:800]}" for i, o in enumerate(executed_outputs))
    data = llm.chat_json(
        [{"role": "system", "content": _JUDGE_SYS},
         {"role": "user", "content": f"Hypothesis: {hypothesis}\n\nExecuted evidence:\n{ev}"}],
        temperature=0.1,
    )
    if isinstance(data, dict) and data.get("verdict") in ("supported", "falsified", "undecided"):
        return data["verdict"], str(data.get("reason", ""))[:400]
    # Heuristic fallback (no LLM referee): record as undecided but note execution.
    ran_clean = any(o.strip() and "error" not in o.lower() for o in executed_outputs)
    return "undecided", ("referee unavailable; experiment executed cleanly" if ran_clean
                         else "referee unavailable; no decisive signal")


def _fallback_experiment(hypothesis: str) -> str:
    """A deterministic, self-contained experiment used when no LLM can author one.
    It measurably exercises the sandbox + geometry pipeline (recursion vs memoized
    call counts) so offline runs still produce executed_result evidence."""
    h = hypothesis.replace(chr(34), "'")[:200]
    return (
        "# offline smoke experiment for hypothesis:\n"
        f"# {h}\n"
        "def fib(n):\n"
        "    return n if n < 2 else fib(n-1) + fib(n-2)\n"
        "from functools import lru_cache\n"
        "@lru_cache(None)\n"
        "def mfib(n):\n"
        "    return n if n < 2 else mfib(n-1) + mfib(n-2)\n"
        "calls = {'plain': 0}\n"
        "def cfib(n):\n"
        "    calls['plain'] += 1\n"
        "    return n if n < 2 else cfib(n-1) + cfib(n-2)\n"
        "cfib(20)\n"
        "print('plain_recursive_calls_for_fib20 =', calls['plain'])\n"
        "print('memoized_reduces_calls =', calls['plain'] > 21)\n"
    )


def _mutate(hypothesis: str, reason: str) -> str:
    text = llm.chat(
        [{"role": "system", "content": "Revise the falsified hypothesis into a sharper, still-"
          "falsifiable version that accounts for the refuting evidence. One sentence."},
         {"role": "user", "content": f"Hypothesis: {hypothesis}\nRefuted because: {reason}"}],
        temperature=0.5,
    )
    return (text or f"{hypothesis} (revised: narrower conditions)").strip()


# ── the loop ──────────────────────────────────────────────────────────────────
def run(question: str, panel_names: list[str] | None = None, cycles: int = 2,
        printer=None, run_icgg_domain: str | None = "arith") -> dict:
    store = Store()
    panel = agents.resolve_panel(panel_names)

    _p(printer, "\n== PROBLEM COMPILER ==")
    compiled = compiler.compile_problem(question)
    run_id = store.create_run(question, compiled)
    _p(printer, f"restated: {compiled['restated']}")
    for h in compiled["hypotheses"]:
        _p(printer, f"  hypothesis: {h}")
    _p(printer, f"run id: {run_id}   panel: {', '.join(panel)}")

    # Seed hypotheses.
    active = [store.add_hypothesis(run_id, h, cycle=0) for h in compiled["hypotheses"]]
    hyp_text = {hid: t for hid, t in zip(active, compiled["hypotheses"])}

    report_cycles = []
    for cyc in range(cycles):
        _p(printer, f"\n===== CYCLE {cyc+1}/{cycles} =====")
        if not active:
            _p(printer, "(no active hypotheses left)")
            break
        top = active[0]
        top_text = hyp_text[top]

        # --- DEBATE (agent_claim evidence; tool outputs are executed_result) ---
        _p(printer, "\n-- DEBATE NETWORK (tool-enabled) --")
        turns = agents.debate(question, top_text, panel, rounds=2, use_tools=True)
        for t in turns:
            store.add_evidence(run_id, "agent_claim", t["content"],
                               source_ref=f"{t['agent']}:r{t['round']}", hypothesis_id=top)
            if t.get("tool_call"):
                tc = t["tool_call"]
                store.add_evidence(run_id, "executed_result",
                                   f"TOOL {tc['tool']} {json.dumps(tc['args'])}\n{tc['result']}",
                                   source_ref=f"tool:{tc['tool']}", hypothesis_id=top)
                _p(printer, f"[{t['title']} r{t['round']}] used TOOL {tc['tool']} -> "
                            f"{tc['result'][:120]}")
            _p(printer, f"[{t['title']} r{t['round']}] {t['content'][:200]}")

        # --- EXECUTE (executed_result evidence w/ geometry) ---
        _p(printer, "\n-- EXECUTION ENGINE --")
        executed_outputs = []
        for exp in compiled["experiments"][:2]:
            code = _write_experiment(question, top_text, exp["idea"])
            if not code:
                # Offline fallback: a real (labeled) smoke experiment so the
                # execution + geometry pipeline still yields evidence with no LLM.
                code = _fallback_experiment(top_text)
                _p(printer, "  (no LLM — running deterministic smoke experiment)")
            res = geometry.run_with_geometry(code, timeout=12)
            out = res.get("stdout", "") or res.get("stderr", "")
            executed_outputs.append(out)
            eid = store.add_evidence(run_id, "executed_result",
                                     f"CODE:\n{code}\n\nOUTPUT:\n{out}",
                                     source_ref="sandbox", hypothesis_id=top,
                                     geometry=res.get("geometry"))
            g = res.get("geometry") or {}
            _p(printer, f"  ran experiment -> evidence {eid} "
                        f"(ast={g.get('ast_nodes')}, depth={g.get('max_call_depth')})")
            _p(printer, f"    output: {out.strip()[:200]}")

        # --- MEASURE / FALSIFY ---
        _p(printer, "\n-- VERDICT --")
        verdict, reason = _judge(top_text, executed_outputs)
        store.set_hypothesis_status(top, verdict, reason)
        _p(printer, f"  [{verdict}] {top_text[:120]}  ({reason[:120]})")

        # --- FALSIFY -> mutate for next cycle ---
        if verdict == "falsified" and cyc + 1 < cycles:
            new_text = _mutate(top_text, reason)
            nid = store.add_hypothesis(run_id, new_text, cycle=cyc + 1)
            hyp_text[nid] = new_text
            active = active[1:] + [nid]
            _p(printer, f"  mutated -> {new_text[:120]}")
        elif verdict == "supported":
            active = active[1:]  # settled; move on
        else:
            active = active[1:] + [top]  # undecided -> revisit later

        report_cycles.append({"cycle": cyc, "hypothesis": top_text,
                              "verdict": verdict, "reason": reason,
                              "experiments_run": len(executed_outputs)})

    # --- COMPRESS + PROMOTE: run a certified grammar-growth experiment ---
    icgg_summary = None
    if run_icgg_domain:
        _p(printer, "\n== GRAMMAR EVOLUTION (ICGG) ==")
        gr = icgg_runner.run_growth(run_icgg_domain, generations=2, seeds=3)
        icgg_summary = {k: v for k, v in gr.items() if k != "grammar"}
        eid = store.add_evidence(run_id, "executed_result",
                                 json.dumps(icgg_summary)[:8000],
                                 source_ref=f"icgg:{run_icgg_domain}")
        added = ecology.register_certified(store, run_icgg_domain,
                                           gr["certified_operators"], evidence_id=eid)
        for c in gr["certified_operators"]:
            if not genome.has(c["name"]):
                genome.add_record("operator", c["name"],
                                  recipe={"domain": run_icgg_domain, "sequence": c["sequence"]},
                                  provenance=[eid], notes=c["reason"])
        _p(printer, f"  reduction: {gr['expanded_reduction']} nodes/task on held-out tasks")
        _p(printer, f"  certified + promoted operators: {added or '(none)'}")

        # Computational Noether Engine — conserved quantity + symmetry operators.
        _p(printer, "\n== COMPUTATIONAL NOETHER ENGINE ==")
        try:
            from . import noether
            cne = noether.run_cne(run_icgg_domain, seeds=3)
            q = cne["conserved_quantity"]
            _p(printer, f"  conserved Q = {q['expression']} "
                        f"(score {q['conservation_score']}, pos_drift {q['pos_drift']})")
            eid2 = store.add_evidence(run_id, "executed_result",
                                      json.dumps({k: v for k, v in cne.items() if k != '_Q'})[:8000],
                                      source_ref=f"noether:{run_icgg_domain}")
            sym_added = ecology.register_certified(
                store, run_icgg_domain, cne["certified_symmetry_operators"], evidence_id=eid2)
            for c in cne["certified_symmetry_operators"]:
                nm = "sym_" + "_".join(c["sequence"])
                if not genome.has(nm):
                    genome.add_record("symmetry_operator", nm,
                                      recipe={"domain": run_icgg_domain, "sequence": c["sequence"],
                                              "conserved_quantity": q["expression"]},
                                      provenance=[eid2], notes="Noether symmetry, certified")
            _p(printer, f"  certified symmetry operators: {sym_added or '(none — symmetries were trivial here)'}")
        except Exception as e:
            _p(printer, f"  (CNE skipped: {str(e)[:120]})")

    store.finish_run(run_id, status="done")
    result = {"run_id": run_id, "compiled": compiled, "cycles": report_cycles,
              "icgg": icgg_summary,
              "hypotheses": store.hypotheses(run_id=run_id),
              "evidence_counts": _evidence_counts(store, run_id)}
    store.close()
    return result


def _evidence_counts(store: Store, run_id: str) -> dict:
    ev = store.evidence(run_id=run_id)
    out: dict = {}
    for e in ev:
        out[e["kind"]] = out.get(e["kind"], 0) + 1
    return out
