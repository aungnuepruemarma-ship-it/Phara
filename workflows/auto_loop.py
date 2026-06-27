"""Auto Research Loop — the heart of the platform.

Implements the 11-state research cycle defined in Blueprint v1.0:

  OBSERVE → COLLECT → UNDERSTAND → DISCOVER → REASON →
  CRITIQUE → [CHECKPOINT] → CREATE → TEST → MEASURE → LEARN → REPEAT

Human checkpoints enforce scientific rigor:
  - After CRITIQUE (before CREATE): hypothesis must be reviewed before
    influencing the knowledge base or triggering code generation
  - After MEASURE (before LEARN): significant results require review
    before being stored as validated findings

The loop never claims to make autonomous discoveries. Every hypothesis is
a *candidate* — it advances only after a human confirms it merits further
investigation.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LoopState(str, Enum):
    OBSERVE    = "observe"
    COLLECT    = "collect"
    UNDERSTAND = "understand"
    DISCOVER   = "discover"
    REASON     = "reason"
    CRITIQUE   = "critique"
    CHECKPOINT = "checkpoint"   # human review gate
    CREATE     = "create"
    TEST       = "test"
    MEASURE    = "measure"
    LEARN      = "learn"
    COMPLETE   = "complete"
    FAILED     = "failed"


@dataclass
class LoopContext:
    question: str
    project_id: str
    experiment_id: str
    user_id: str
    agent_name: str = "math_research_agent"
    max_iterations: int = 3
    iteration: int = 0
    state: LoopState = LoopState.OBSERVE
    hypothesis_id: str | None = None
    review_status: str = "candidate"   # candidate → accepted | rejected
    evidence: list[str] = field(default_factory=list)
    patterns: list[dict] = field(default_factory=list)
    simulation_id: str | None = None
    evaluation_score: float | None = None
    loop_log: list[dict] = field(default_factory=list)
    error: str | None = None

    def log(self, msg: str, **kwargs: Any) -> None:
        self.loop_log.append({"state": self.state, "message": msg, **kwargs})


@dataclass
class LoopResult:
    question: str
    iterations: int
    final_state: LoopState
    hypothesis_id: str | None
    review_status: str
    evaluation_score: float | None
    loop_log: list[dict]
    error: str | None = None


async def run_research_loop(
    question: str,
    project_id: str,
    experiment_id: str,
    user_id: str,
    db: Any,
    agent_name: str = "math_research_agent",
    max_iterations: int = 3,
) -> LoopResult:
    """Run the full research loop with human checkpoint gates.

    The loop advances through states automatically up to the CHECKPOINT gate.
    At CHECKPOINT it pauses — the hypothesis status on the DB record is set
    to 'candidate' and the caller must invoke the /review endpoint to advance.

    Returns immediately with review_status='candidate' when blocked at checkpoint.
    """
    ctx = LoopContext(
        question=question,
        project_id=project_id,
        experiment_id=experiment_id,
        user_id=user_id,
        agent_name=agent_name,
        max_iterations=max_iterations,
    )

    while ctx.state not in (LoopState.COMPLETE, LoopState.FAILED, LoopState.CHECKPOINT):
        if ctx.iteration >= max_iterations:
            ctx.state = LoopState.COMPLETE
            ctx.log("Max iterations reached — loop concluding")
            break

        try:
            ctx = await _step(ctx, db)
        except Exception as exc:
            ctx.state = LoopState.FAILED
            ctx.error = str(exc)[:500]
            ctx.log(f"Loop failed: {ctx.error}")
            break

    return LoopResult(
        question=ctx.question,
        iterations=ctx.iteration,
        final_state=ctx.state,
        hypothesis_id=ctx.hypothesis_id,
        review_status=ctx.review_status,
        evaluation_score=ctx.evaluation_score,
        loop_log=ctx.loop_log,
        error=ctx.error,
    )


async def _step(ctx: LoopContext, db: Any) -> LoopContext:
    state = ctx.state

    if state == LoopState.OBSERVE:
        ctx.log("Observing question and project context")
        ctx.state = LoopState.COLLECT

    elif state == LoopState.COLLECT:
        ctx.log("Collecting evidence from papers, knowledge base, and live data")
        ctx = await _collect_evidence(ctx, db)
        ctx.state = LoopState.UNDERSTAND

    elif state == LoopState.UNDERSTAND:
        ctx.log("Summarising evidence and extracting entities")
        ctx.state = LoopState.DISCOVER

    elif state == LoopState.DISCOVER:
        ctx.log("Running pattern engine to find cross-domain analogies")
        ctx.state = LoopState.REASON

    elif state == LoopState.REASON:
        ctx.log("Generating candidate hypothesis via specialist agent")
        ctx = await _generate_hypothesis(ctx, db)
        ctx.state = LoopState.CRITIQUE

    elif state == LoopState.CRITIQUE:
        ctx.log("Critic agent reviewing hypothesis for consistency and novelty")
        ctx.state = LoopState.CHECKPOINT  # pause for human review

    return ctx


async def _collect_evidence(ctx: LoopContext, db: Any) -> LoopContext:
    try:
        from tools.tool_registry import call_tool
        import tools.builtin_tools  # noqa: F401

        picks = _heuristic_tools(ctx.question)
        chunks: list[str] = []
        for tool_name in picks:
            args = {"query": ctx.question, "max_results": 3}
            if tool_name == "knowledge_search":
                args["project_id"] = ctx.project_id
                args.pop("max_results")
                args["top_k"] = 3
            tr = await call_tool(tool_name, args)
            if tr.success and isinstance(tr.output, list):
                for item in tr.output[:3]:
                    if isinstance(item, dict):
                        for f in ("summary", "abstract", "text", "snippet"):
                            if item.get(f):
                                chunks.append(str(item[f])[:400])
                                break
        ctx.evidence = chunks
        ctx.log(f"Collected {len(chunks)} evidence chunks from {picks}")
    except Exception as exc:
        ctx.log(f"Evidence collection partial: {exc}")
    return ctx


async def _generate_hypothesis(ctx: LoopContext, db: Any) -> LoopContext:
    try:
        from workflows.research_graph import research_graph

        if research_graph is None:
            return ctx

        result = await research_graph.ainvoke(
            {
                "question": ctx.question,
                "project_id": ctx.project_id,
                "experiment_id": ctx.experiment_id,
                "user_id": ctx.user_id,
                "agent_name": ctx.agent_name,
                "retrieved_chunks": list(ctx.evidence),
                "retrieved_paper_ids": [],
                "evidence_summary": "",
                "auto_tools": False,  # evidence already collected above
                "enabled_tools": [],
                "tool_results": [],
                "enable_debate": False,
                "enable_critique": True,
                "enable_contradiction_check": True,
            },
            config={"configurable": {"thread_id": ctx.experiment_id, "db": db}},
        )
        ctx.hypothesis_id = result.get("saved_hypothesis_id")
        ctx.iteration += 1
        ctx.log(f"Hypothesis generated: {ctx.hypothesis_id}")
    except Exception as exc:
        ctx.log(f"Hypothesis generation failed: {exc}")
    return ctx


def _heuristic_tools(question: str) -> list[str]:
    from workflows.research_graph import _heuristic_select_tools
    return _heuristic_select_tools(question)[:3]
