"""
Report Service — generates structured research reports for a project.

A report aggregates all experiments + hypotheses, calls the LLM
to synthesize findings, and returns both raw data and a synthesis section.
"""
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.experiment import Experiment
from app.models.hypothesis import Hypothesis
from app.models.project import Project
from app.schemas.report import ProjectReport

_repo_root = str(Path(__file__).resolve().parents[4])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)


async def _synthesize(hypotheses: list[Hypothesis], project_name: str) -> str:
    """Use LLM to synthesize all hypotheses into a narrative report."""
    if not settings.llm_api_key or not hypotheses:
        if not hypotheses:
            return "No hypotheses have been generated for this project yet."
        return "\n\n".join(
            f"**{h.question}**\n{h.hypothesis_text}" for h in hypotheses[:10]
        )

    items = "\n\n".join(
        f"[{i+1}] Question: {h.question}\nHypothesis: {h.hypothesis_text}\n"
        f"Agent: {h.agent_used}  Confidence: {h.confidence_score or 'N/A'}"
        for i, h in enumerate(hypotheses[:20])
    )
    prompt = (
        f"Project: {project_name}\n\n"
        f"Research hypotheses generated so far:\n{items}\n\n"
        "Write a concise research synthesis report (3-5 paragraphs) that:\n"
        "1. Summarizes the main research threads and findings\n"
        "2. Highlights converging evidence across hypotheses\n"
        "3. Identifies open questions and contradictions\n"
        "4. Suggests the most promising directions for future work\n"
        "Use clear, academic prose. Use markdown formatting."
    )
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {"role": "system", "content": "You are a scientific research synthesizer."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.5,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        return f"Synthesis unavailable: {exc}"


async def generate_report(db: AsyncSession, project_id: uuid.UUID) -> ProjectReport:
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if project is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Project not found")

    exp_result = await db.execute(
        select(Experiment)
        .options(selectinload(Experiment.hypotheses))
        .where(Experiment.project_id == project_id)
        .order_by(Experiment.created_at)
    )
    experiments = list(exp_result.scalars().all())

    all_hyps: list[Hypothesis] = []
    for exp in experiments:
        all_hyps.extend(exp.hypotheses)

    agent_counts: dict[str, int] = {}
    confidences: list[float] = []
    for h in all_hyps:
        agent_counts[h.agent_used] = agent_counts.get(h.agent_used, 0) + 1
        if h.confidence_score is not None:
            confidences.append(h.confidence_score)

    top_agents = sorted(agent_counts, key=lambda k: -agent_counts[k])
    avg_conf = sum(confidences) / len(confidences) if confidences else None

    synthesis = await _synthesize(all_hyps, project.name)

    hyps_out = [
        {
            "id": str(h.id),
            "question": h.question,
            "hypothesis_text": h.hypothesis_text,
            "agent_used": h.agent_used,
            "confidence_score": h.confidence_score,
            "created_at": h.created_at.isoformat(),
        }
        for h in all_hyps
    ]

    return ProjectReport(
        project_id=project.id,
        project_name=project.name,
        generated_at=datetime.now(timezone.utc),
        experiment_count=len(experiments),
        hypothesis_count=len(all_hyps),
        hypotheses=hyps_out,
        synthesis=synthesis,
        top_agents=top_agents,
        avg_confidence=avg_conf,
    )
