"""Debate Network — specialist agents debating a hypothesis.

Round 1: independent perspectives. Round 2: cross-talk (each agent sees peers).
Devil's Advocate always proposes the cheapest falsifying test. Returns turns as
plain dicts; every claim is stored by the caller as agent_claim evidence (the
lowest tier — never sufficient for promotion).
"""
from __future__ import annotations

from . import llm

AGENTS: dict[str, dict] = {
    "architect": {
        "title": "Architect AI",
        "system": "You are the research architect. Turn a question into a concrete plan: the key "
                  "sub-questions and the single most decisive experiment to run first.",
    },
    "math": {
        "title": "Mathematics AI",
        "system": "You are a rigorous mathematician on a research panel. Analyze the hypothesis "
                  "formally: definitions, quantitative structure, provable/disprovable parts.",
    },
    "physics": {
        "title": "Physics AI",
        "system": "You are a physicist on a research panel. Analyze mechanisms, conservation "
                  "constraints, scaling behaviour, and what measurement would decide the question.",
    },
    "cs": {
        "title": "Computer Science AI",
        "system": "You are a computer scientist on a research panel. Analyze algorithmic content, "
                  "complexity, computability, and how to implement a decisive test in code.",
    },
    "biology": {
        "title": "Biology AI",
        "system": "You are a biologist on a research panel. Analyze evolutionary, adaptive, and "
                  "systems-level mechanisms and what empirical signature would confirm or deny them.",
    },
    "philosophy": {
        "title": "Philosophy AI",
        "system": "You are a philosopher of science on a research panel. Check definitions for "
                  "coherence, expose hidden assumptions, and demand operational, falsifiable claims.",
    },
    "systems": {
        "title": "Systems AI",
        "system": "You are a systems theorist on a research panel. Analyze feedback, emergence, "
                  "constraints, and the boundary conditions under which the hypothesis holds or breaks.",
    },
    "critic": {
        "title": "Critic AI",
        "system": "You are a rigorous scientific critic. Do NOT propose a new hypothesis; find "
                  "logical gaps, unsupported claims, and alternative explanations the evidence cannot rule out.",
    },
    "devil": {
        "title": "Devil's Advocate AI",
        "system": "You are the Devil's Advocate. Assume the hypothesis is FALSE and argue it. Then "
                  "propose the single CHEAPEST concrete experiment (runnable Python) that would falsify it "
                  "if it is wrong. End with a line 'FALSIFYING TEST: <one sentence>'.",
    },
}

# Sensible default panel if the user names none.
DEFAULT_PANEL = ["math", "cs", "physics", "critic", "devil"]

_ALIASES = {
    "math_research_agent": "math", "ai_research_agent": "cs", "cs_research_agent": "cs",
    "physics_research_agent": "physics", "biology_research_agent": "biology",
    "critic_agent": "critic", "devils_advocate": "devil", "devil's advocate": "devil",
    "devils_advocate_agent": "devil", "philosophy_agent": "philosophy",
    "systems_agent": "systems", "architect_agent": "architect",
}


def resolve_panel(names: list[str] | None) -> list[str]:
    if not names:
        return list(DEFAULT_PANEL)
    out: list[str] = []
    for n in names:
        key = _ALIASES.get(n.strip().lower(), n.strip().lower())
        if key in AGENTS and key not in out:
            out.append(key)
    return out or list(DEFAULT_PANEL)


def _run_agent(key: str, question: str, hypothesis: str,
               peer_context: str = "", extra_instruction: str = "") -> dict:
    spec = AGENTS[key]
    parts = [f"Research question: {question}"]
    if hypothesis:
        parts.append(f"Hypothesis under discussion:\n{hypothesis}")
    if peer_context:
        parts.append(f"What other experts said:\n{peer_context}")
    if extra_instruction:
        parts.append(extra_instruction)
    parts.append("Respond in 2-5 sentences. Be concrete and falsifiable.")
    user = "\n\n".join(parts)

    text = llm.chat(
        [{"role": "system", "content": spec["system"]}, {"role": "user", "content": user}],
        temperature=0.7,
    )
    if not text:
        text = f"[{spec['title']} unavailable — no LLM configured]"
    return {"agent": key, "title": spec["title"], "content": text.strip()}


def debate(question: str, hypothesis: str, panel: list[str], rounds: int = 2) -> list[dict]:
    """Run the debate. Returns a flat list of turn dicts with a 'round' field."""
    turns: list[dict] = []

    # Round 1 — independent perspectives.
    round1 = [_run_agent(k, question, hypothesis) for k in panel]
    for t in round1:
        t["round"] = 1
    turns.extend(round1)

    if rounds < 2 or len(panel) < 2:
        return turns

    # Round 2 — cross-talk. Each agent sees a digest of the others.
    def digest(exclude: str) -> str:
        return "\n\n".join(f"[{t['title']}]: {t['content'][:500]}"
                           for t in round1 if t["agent"] != exclude)

    for k in panel:
        instr = ("You previously gave your view. Now respond to the panel: agree, challenge, or "
                 "refine, and sharpen the decisive experiment.")
        t = _run_agent(k, question, hypothesis, peer_context=digest(k), extra_instruction=instr)
        t["round"] = 2
        turns.append(t)
    return turns
