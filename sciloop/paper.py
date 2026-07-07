"""Research Paper Generator — renders a run into a markdown paper.

Everything cites evidence ids so claims trace back to what actually ran. No
LLM required (a factual report); the debate/verdict text is quoted from stored
evidence.
"""
from __future__ import annotations

import json
import time

from . import config
from .evidence import Store


def generate(store: Store, run_id: str) -> str:
    run = store.get_run(run_id)
    if not run:
        raise ValueError(f"No run {run_id!r}")
    compiled = json.loads(run.get("compiled") or "{}")
    hyps = store.hypotheses(run_id=run_id)
    ev = store.evidence(run_id=run_id)
    executed = [e for e in ev if e["kind"] == "executed_result"]

    lines: list[str] = []
    W = lines.append
    W(f"# {compiled.get('restated') or run['question']}")
    W("")
    W(f"*SciLoop run `{run_id}` — generated {time.strftime('%Y-%m-%d %H:%M')}*")
    W("")
    W("## 1. Problem")
    W(f"**Question.** {run['question']}")
    if compiled.get("sub_questions"):
        W("")
        W("**Sub-questions.**")
        for s in compiled["sub_questions"]:
            W(f"- {s}")
    W("")

    W("## 2. Hypotheses and verdicts")
    for h in hyps:
        W(f"- **[{h['status']}]** {h['text']}"
          + (f"  \n  _{h['reason']}_" if h.get("reason") else ""))
    W("")

    W("## 3. Experiments (executed evidence)")
    if not executed:
        W("_No experiments were executed in this run._")
    for i, e in enumerate(executed, 1):
        geom = json.loads(e["geometry"]) if e.get("geometry") else None
        W(f"### Experiment {i} — evidence `{e['id']}`")
        W("```")
        W((e["content"] or "").strip()[:2000])
        W("```")
        if geom:
            W(f"*Execution geometry:* ast_nodes={geom.get('ast_nodes')}, "
              f"max_call_depth={geom.get('max_call_depth')}, "
              f"distinct_lines={geom.get('distinct_lines')}, "
              f"top_calls={list((geom.get('call_counts') or {}).items())[:3]}")
        W("")

    ops = store.operators(status="certified")
    W("## 4. Promoted operators (certified grammar growth)")
    if ops:
        for o in ops:
            W(f"- `{o['name']}` (domain={o['domain']}, fitness={round(o['fitness'],3)}, "
              f"uses={o['uses']})")
    else:
        W("_No operators certified in this run._")
    W("")

    W("## 5. Provenance")
    W(f"- Total evidence rows: {len(ev)} "
      f"(executed={len(executed)}, "
      f"agent_claim={len([e for e in ev if e['kind']=='agent_claim'])}, "
      f"retrieved={len([e for e in ev if e['kind']=='retrieved_source'])})")
    W("- Promotion rule: only `executed_result` / `retrieved_source` evidence "
      "counts toward a verdict; agent claims alone are never sufficient.")
    W("")

    md = "\n".join(lines)
    config.ensure_workspace()
    path = config.PAPERS_DIR / f"{run_id}.md"
    path.write_text(md)
    store.finish_run(run_id, status=run.get("status", "done"), report_path=str(path))
    return str(path)
