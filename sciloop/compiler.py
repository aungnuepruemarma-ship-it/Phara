"""Problem Compiler — turns a raw question into a structured, falsifiable plan.

Output (CompiledProblem):
  restated:      one-sentence restatement
  sub_questions: list[str]
  hypotheses:    list[str]  (each falsifiable)
  experiments:   list[{idea, success_criterion}]  (runnable-in-Python intent)

Falls back to a deterministic heuristic when no LLM is available so the whole
loop still runs offline.
"""
from __future__ import annotations

from . import llm

_SYSTEM = (
    "You are a Problem Compiler for a scientific runtime. Convert the user's question into a "
    "structured research plan of FALSIFIABLE hypotheses and concrete experiments that can be "
    "run as short Python programs. Respond ONLY with JSON of the form:\n"
    '{"restated": "...", "sub_questions": ["..."], "hypotheses": ["..."], '
    '"experiments": [{"idea": "...", "success_criterion": "..."}]}'
)


def compile_problem(question: str) -> dict:
    data = llm.chat_json(
        [{"role": "system", "content": _SYSTEM},
         {"role": "user", "content": f"Question: {question}"}],
        temperature=0.3,
    )
    if isinstance(data, dict) and data.get("hypotheses"):
        return _normalize(question, data)
    return _heuristic(question)


def _normalize(question: str, data: dict) -> dict:
    def _strlist(x):
        return [str(i).strip() for i in x if str(i).strip()] if isinstance(x, list) else []

    exps = []
    for e in (data.get("experiments") or []):
        if isinstance(e, dict) and e.get("idea"):
            exps.append({"idea": str(e["idea"])[:400],
                         "success_criterion": str(e.get("success_criterion", ""))[:300]})
        elif isinstance(e, str) and e.strip():
            exps.append({"idea": e.strip()[:400], "success_criterion": ""})
    return {
        "restated": str(data.get("restated") or question)[:400],
        "sub_questions": _strlist(data.get("sub_questions"))[:6],
        "hypotheses": _strlist(data.get("hypotheses"))[:5] or [question],
        "experiments": exps[:4] or _heuristic(question)["experiments"],
    }


def _heuristic(question: str) -> dict:
    q = question.strip().rstrip("?")
    return {
        "restated": q,
        "sub_questions": [p.strip() for p in q.split(" and ") if p.strip()][:6] or [q],
        "hypotheses": [f"{q} — this holds under stated conditions."],
        "experiments": [{
            "idea": ("Write a small self-contained Python simulation or numerical check that "
                     f"illustrates or stresses the claim: {q}. Print labeled results."),
            "success_criterion": "The program runs and its printed output supports or contradicts the claim.",
        }],
    }
