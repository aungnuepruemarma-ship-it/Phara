"""
collaboration_service — multi-agent "roundtable".

Selected agents each give a perspective, then see each other's views and respond
(cross-talk), a pattern finder mines structural patterns shared across their
hypotheses, and a moderator synthesizes one final answer. The final answer is
persisted as a Hypothesis so it shows in history/experiments.
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.research import (
    AgentTurn,
    DomainPatternOut,
    RoundtableRequest,
    RoundtableResult,
)

_repo_root = str(Path(__file__).resolve().parents[4])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# Cap concurrent agents to bound latency / LLM usage per turn.
_MAX_AGENTS = 4

_PERSPECTIVE_INSTRUCTION = (
    "You are one of several expert agents on a research panel. Give your own "
    "perspective on the question from your domain of expertise. Be specific and concise."
)
_REBUTTAL_INSTRUCTION = (
    "You are on a research panel. You have now seen the other experts' views. "
    "Respond to them: note where you agree, challenge what you disagree with, and "
    "refine your own position. Reference the other agents by their domain."
)


async def run_roundtable(
    req: RoundtableRequest, db: AsyncSession, current_user: User
) -> RoundtableResult:
    from agents.agent_registry import AGENT_REGISTRY, get_agent
    from agents.base_agent import AgentInput
    from app.config import settings

    # Resolve + de-dup selected agents, capped.
    names: list[str] = []
    for n in req.agent_names:
        if n in AGENT_REGISTRY and n not in names:
            names.append(n)
    names = names[:_MAX_AGENTS]
    if not names:
        names = ["math_research_agent"]

    history_text = _format_history(req.history)

    # 1 — Evidence (best-effort; empty is fine).
    chunks: list[str] = []
    paper_ids: list[str] = []
    try:
        from workflows.base_step import PipelineContext
        from workflows.steps.retrieve_papers import RetrievePapersStep

        ctx = PipelineContext(
            question=req.question,
            project_id=str(req.project_id),
            experiment_id="",
            user_id=str(current_user.id),
        )
        ctx = await RetrievePapersStep(top_k=settings.retrieval_top_k).execute(ctx)
        chunks = ctx.retrieved_chunks
        paper_ids = ctx.retrieved_paper_ids
    except Exception:
        chunks, paper_ids = [], []

    turns: list[AgentTurn] = []

    # 1b — Real-time data tools (run before round 1 so all agents see live data).
    tool_results: list[dict] = []
    data_tools = [t for t in (req.tools or []) if t != "code_sandbox"]
    use_sandbox = "code_sandbox" in (req.tools or [])
    if data_tools:
        tool_results = await _run_data_tools(data_tools, req.question, str(req.project_id))
        live = _summarize_tool_results(tool_results)
        if live:
            chunks = list(chunks) + [live]

    # 2 — Round 1: independent perspectives (parallel).
    async def _perspective(name: str) -> AgentTurn:
        agent = get_agent(name)
        out = await agent.arun(AgentInput(
            question=req.question,
            context=chunks,
            parameters={"instruction": _PERSPECTIVE_INSTRUCTION, "history": history_text},
        ))
        return AgentTurn(agent_name=name, role="perspective",
                         content=out.hypothesis, confidence=float(out.confidence))

    round1 = await asyncio.gather(*[_perspective(n) for n in names])
    turns.extend(round1)

    # 2b — Experiment: the panel writes + runs Python in the sandbox to test the
    # leading hypothesis. Its output is injected into round 2 + synthesis.
    experiment_turn: AgentTurn | None = None
    experiment_context = ""
    if use_sandbox:
        experiment_turn = await _run_experiment(req.question, round1)
        if experiment_turn:
            turns.append(experiment_turn)
            experiment_context = experiment_turn.content

    # 3 + 4 run concurrently — both depend only on round-1 outputs, so mining
    # patterns and the cross-talk round happen in parallel to save a stage.
    async def _mine() -> list[DomainPatternOut]:
        if len(round1) < 2:
            return []
        try:
            from intelligence.pattern_miner import mine_patterns

            mined = await mine_patterns([t.content for t in round1])
            return [
                DomainPatternOut(
                    pattern_type=p.pattern_type,
                    description=p.description,
                    domains_seen=list(p.domains_seen or []),
                    confidence=float(p.confidence),
                )
                for p in mined
            ][:6]
        except Exception:
            return []

    async def _crosstalk() -> list[AgentTurn]:
        if len(names) < 2:
            return []
        peer_blocks = {name: _peer_digest(round1, exclude=name) for name in names}

        async def _rebuttal(name: str) -> AgentTurn:
            agent = get_agent(name)
            peer = peer_blocks[name]
            if experiment_context:
                peer = f"{peer}\n\n[code_sandbox experiment]:\n{experiment_context[:800]}"
            out = await agent.arun(AgentInput(
                question=req.question,
                context=chunks,
                parameters={
                    "instruction": _REBUTTAL_INSTRUCTION,
                    "peer_context": peer,
                    "history": history_text,
                },
            ))
            return AgentTurn(agent_name=name, role="rebuttal",
                             content=out.hypothesis, confidence=float(out.confidence))

        return list(await asyncio.gather(*[_rebuttal(n) for n in names]))

    patterns, round2 = await asyncio.gather(_mine(), _crosstalk())
    turns.extend(round2)

    # 5 — Synthesis (moderator).
    final_text, final_conf = await _synthesize(
        req.question, turns, patterns, history_text
    )

    # 6 — Persist final answer as a Hypothesis (auto-create experiment).
    saved_id = await _save_final(
        db, req, current_user, final_text, final_conf, paper_ids, names
    )

    return RoundtableResult(
        turns=turns,
        final_text=final_text,
        final_confidence=final_conf,
        patterns=patterns,
        tool_results=tool_results,
        saved_hypothesis_id=saved_id,
        retrieved_paper_count=len(paper_ids),
    )


def _format_history(history) -> str:
    if not history:
        return ""
    lines = []
    for h in history[-6:]:
        who = "You" if h.role == "user" else "Panel"
        lines.append(f"{who}: {h.content[:500]}")
    return "\n".join(lines)


def _peer_digest(turns: list[AgentTurn], exclude: str) -> str:
    return "\n\n".join(
        f"[{t.agent_name}]: {t.content[:600]}"
        for t in turns
        if t.agent_name != exclude and t.role in ("perspective", "experiment")
    )


def _tool_args(name: str, question: str, project_id: str) -> dict:
    """Map a data tool name to call args (mirrors workflows/research_graph tool_use_node)."""
    if name == "knowledge_search":
        return {"query": question, "project_id": project_id, "top_k": 5}
    if name in ("arxiv_search", "web_search", "semantic_scholar_search",
                "pubmed_search", "crossref_search", "openalex_search"):
        return {"query": question, "max_results": 5}
    if name == "wikipedia_search":
        return {"query": question, "top_k": 3}
    if name == "extract_entities":
        return {"text": question}
    return {"query": question}


async def _run_data_tools(tool_names: list[str], question: str, project_id: str) -> list[dict]:
    import tools.builtin_tools  # noqa: F401 — ensure registration
    from tools.tool_registry import TOOL_REGISTRY, call_tool

    valid = [t for t in tool_names if t in TOOL_REGISTRY][:5]

    async def _one(name: str) -> dict:
        tr = await call_tool(name, _tool_args(name, question, project_id))
        return tr.to_dict()

    if not valid:
        return []
    return list(await asyncio.gather(*[_one(n) for n in valid]))


def _summarize_tool_results(tool_results: list[dict]) -> str:
    parts: list[str] = []
    for tr in tool_results:
        if not tr.get("success"):
            continue
        out = tr.get("output")
        name = tr.get("tool_name", "tool")
        if isinstance(out, list) and out:
            preview = str(out[:3])[:600]
        elif out:
            preview = str(out)[:600]
        else:
            continue
        parts.append(f"[{name}]: {preview}")
    if not parts:
        return ""
    return "Live data fetched for this question:\n" + "\n".join(parts)


async def _run_experiment(question: str, round1: list[AgentTurn]) -> AgentTurn | None:
    """Have the panel write a short Python experiment and run it in the sandbox."""
    import re

    from agents.llm_client import resilient_chat

    leading = max(round1, key=lambda t: t.confidence) if round1 else None
    hypothesis = leading.content if leading else ""

    system = (
        "You are a computational scientist. Write a SHORT, self-contained Python 3 "
        "experiment (standard library only) that empirically probes or illustrates the "
        "research idea below — e.g. a small simulation, numerical check, or statistical "
        "test. It MUST print() clear, labeled results. Keep it under ~40 lines and fast "
        "(<5s). Respond with ONLY a ```python code block."
    )
    user = f"Question: {question}\n\nLeading hypothesis:\n{hypothesis[:800]}"

    code_text = await resilient_chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.3,
    )
    if not code_text:
        return None

    m = re.search(r"```(?:python)?\s*(.*?)```", code_text, re.DOTALL)
    code = (m.group(1) if m else code_text).strip()
    if not code:
        return None

    import tools.builtin_tools  # noqa: F401
    from tools.tool_registry import call_tool

    tr = await call_tool("code_sandbox", {"code": code, "timeout": 10})
    out = tr.output or {}
    stdout = (out.get("stdout") or "").strip()
    stderr = (out.get("stderr") or "").strip()
    result_block = stdout if stdout else (f"(no output)\n{stderr}" if stderr else "(no output)")

    content = (
        f"**Experiment run in the code sandbox:**\n\n```python\n{code}\n```\n\n"
        f"**Output:**\n```\n{result_block[:1500]}\n```"
    )
    confidence = 0.8 if (tr.success and stdout and not out.get("timed_out")) else 0.3
    return AgentTurn(agent_name="code_sandbox", role="experiment",
                     content=content, confidence=confidence)


async def _synthesize(question, turns, patterns, history_text) -> tuple[str, float]:
    from agents.llm_client import resilient_chat

    contributions = "\n\n".join(
        f"[{t.agent_name} — {t.role}]: {t.content[:700]}" for t in turns
    )
    pattern_block = ""
    if patterns:
        pattern_block = "\n\nCross-domain structural patterns detected across the panel:\n" + "\n".join(
            f"- {p.pattern_type}: {p.description[:200]}" for p in patterns
        )
    history_block = f"\n\nEarlier conversation:\n{history_text}" if history_text else ""

    system = (
        "You are the moderator of a multi-agent research panel. Several expert agents "
        "from different domains have debated a question. Synthesize their contributions "
        "into ONE coherent, well-reasoned final answer. Integrate the strongest points, "
        "resolve disagreements explicitly, and note remaining open questions. Use the "
        "detected cross-domain patterns where relevant."
    )
    user = (
        f"Question: {question}"
        f"{history_block}\n\n"
        f"Panel contributions:\n{contributions}"
        f"{pattern_block}\n\n"
        'Respond with JSON: {"answer": "<final synthesized answer in markdown>", '
        '"confidence": 0.0-1.0}'
    )

    text = await resilient_chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.4,
    )
    if not text:
        # Fallback: stitch the contributions if the LLM is unavailable.
        joined = "\n\n".join(f"**{t.agent_name}**: {t.content}" for t in turns)
        return (
            "The panel could not reach a synthesized answer (model unavailable). "
            "Here are the individual contributions:\n\n" + joined,
            0.0,
        )
    import json

    start, end = text.find("{"), text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start:end])
            answer = str(data.get("answer", "")).strip()
            conf = float(data.get("confidence", 0.6))
            if answer:
                return answer, max(0.0, min(1.0, conf))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    return text.strip(), 0.6


async def _save_final(
    db, req, current_user, final_text, final_conf, paper_ids, names
) -> str | None:
    from sqlalchemy import select
    from app.models.experiment import Experiment
    from app.models.hypothesis import Hypothesis

    try:
        experiment_id = req.experiment_id
        if experiment_id is None:
            exp = Experiment(
                id=uuid.uuid4(),
                project_id=req.project_id,
                title=req.question[:120].rstrip(),
                status="completed",
            )
            db.add(exp)
            await db.commit()
            await db.refresh(exp)
            experiment_id = exp.id

        hyp = Hypothesis(
            id=uuid.uuid4(),
            experiment_id=experiment_id,
            question=req.question,
            retrieved_paper_ids=paper_ids,
            evidence_summary="",
            hypothesis_text=final_text,
            agent_used=("roundtable:" + ",".join(names))[:100],
            confidence_score=final_conf,
        )
        db.add(hyp)
        await db.commit()
        await db.refresh(hyp)
        return str(hyp.id)
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        return None
