"""
evaluation_service — persists and retrieves HypothesisEvaluation records.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import HypothesisEvaluation
from app.models.hypothesis import Hypothesis
from app.models.experiment import Experiment


async def evaluate_hypothesis(db: AsyncSession, hypothesis_id: str) -> HypothesisEvaluation | None:
    """Score a hypothesis and persist the result. Returns None if hypothesis not found."""
    hyp = await db.get(Hypothesis, uuid.UUID(hypothesis_id))
    if hyp is None:
        return None

    exp = await db.get(Experiment, hyp.experiment_id)
    project_id = exp.project_id if exp else None
    if project_id is None:
        return None

    # Load prior hypotheses for novelty scoring
    prior_result = await db.execute(
        select(Hypothesis.hypothesis_text)
        .join(Experiment, Hypothesis.experiment_id == Experiment.id)
        .where(Experiment.project_id == project_id)
        .where(Hypothesis.id != hyp.id)
        .order_by(Hypothesis.created_at.desc())
        .limit(10)
    )
    prior_hypotheses = [row[0] for row in prior_result.fetchall()]

    # Load cross-domain insights from existing evaluations (best-effort)
    cross_domain_insights: list[dict] = []

    from evaluation.scorer import score_hypothesis
    from evaluation.benchmarks import run_benchmarks
    import asyncio

    rubric = await score_hypothesis(
        hypothesis_text=hyp.hypothesis_text,
        question=hyp.question,
        evidence_summary=hyp.evidence_summary or "",
        cross_domain_insights=cross_domain_insights,
        prior_hypotheses=prior_hypotheses,
    )

    benchmarks = await run_benchmarks(
        question=hyp.question,
        hypothesis_text=hyp.hypothesis_text,
        evidence_summary=hyp.evidence_summary or "",
        retrieved_chunks=[],
        contradictions=[],
    )

    evaluation = HypothesisEvaluation(
        hypothesis_id=hyp.id,
        project_id=project_id,
        overall_score=rubric.overall,
        verdict=rubric.verdict,
        dimension_scores=[
            {"name": d.name, "score": d.score, "reasoning": d.reasoning}
            for d in rubric.dimensions
        ],
        benchmark_scores=[
            {"name": b.name, "score": b.score, "details": b.details}
            for b in benchmarks
        ],
    )
    db.add(evaluation)
    await db.commit()
    await db.refresh(evaluation)
    return evaluation


async def get_project_evaluations(db: AsyncSession, project_id: str) -> list[HypothesisEvaluation]:
    result = await db.execute(
        select(HypothesisEvaluation)
        .where(HypothesisEvaluation.project_id == uuid.UUID(project_id))
        .order_by(HypothesisEvaluation.created_at.desc())
    )
    return list(result.scalars().all())


async def get_evaluation_summary(db: AsyncSession, project_id: str) -> dict:
    evaluations = await get_project_evaluations(db, project_id)
    if not evaluations:
        return {
            "project_id": project_id,
            "hypothesis_count": 0,
            "avg_score": None,
            "best_agent": None,
            "score_trend": [],
        }

    scores = [e.overall_score for e in evaluations]
    avg_score = round(sum(scores) / len(scores), 4)
    score_trend = list(reversed(scores[:10]))

    # Determine best agent by joining with hypothesis + experiment
    hyp_ids = [e.hypothesis_id for e in evaluations]
    hyp_result = await db.execute(
        select(Hypothesis.id, Hypothesis.agent_used)
        .where(Hypothesis.id.in_(hyp_ids))
    )
    id_to_agent = {row[0]: row[1] for row in hyp_result.fetchall()}

    # Group by agent, compute mean score
    agent_scores: dict[str, list[float]] = {}
    for ev in evaluations:
        agent = id_to_agent.get(ev.hypothesis_id, "unknown")
        agent_scores.setdefault(agent, []).append(ev.overall_score)

    best_agent = max(agent_scores, key=lambda a: sum(agent_scores[a]) / len(agent_scores[a])) if agent_scores else None

    return {
        "project_id": project_id,
        "hypothesis_count": len(evaluations),
        "avg_score": avg_score,
        "best_agent": best_agent,
        "score_trend": score_trend,
    }
