"""
HypothesisScorer — multi-dimensional LLM-based quality scoring.

Scoring dimensions:
  evidence_support  — how well the evidence_summary backs the hypothesis
  specificity       — concreteness and testability
  coherence         — logical consistency
  novelty           — distance from prior hypotheses in the project
  cross_domain      — quality of cross-domain analogies (if any)

Falls back to lightweight heuristics when no LLM is configured.
"""
from __future__ import annotations

import json
import re

import httpx

try:
    from app.config import settings as _settings
except ImportError:
    _settings = None

from evaluation.rubrics import EvaluationRubric, ScoredDimension

_SYSTEM = (
    "You are a scientific hypothesis evaluator. "
    "Given a research question, evidence summary, hypothesis, and optional cross-domain insights, "
    "score the hypothesis on five dimensions (0.0–1.0 each). "
    "Respond ONLY with a JSON object — no prose before or after:\n"
    '{"evidence_support": {"score": 0.0, "reasoning": "..."}, '
    '"specificity": {"score": 0.0, "reasoning": "..."}, '
    '"coherence": {"score": 0.0, "reasoning": "..."}, '
    '"novelty": {"score": 0.0, "reasoning": "..."}, '
    '"cross_domain": {"score": 0.0, "reasoning": "..."}}'
)


async def score_hypothesis(
    hypothesis_text: str,
    question: str,
    evidence_summary: str,
    cross_domain_insights: list[dict] | None = None,
    prior_hypotheses: list[str] | None = None,
) -> EvaluationRubric:
    """Score a hypothesis on all five dimensions. Graceful fallback to heuristics."""
    if _settings and _settings.llm_api_key:
        try:
            return await _llm_score(
                hypothesis_text, question, evidence_summary,
                cross_domain_insights or [], prior_hypotheses or [],
            )
        except Exception:
            pass
    return _heuristic_score(
        hypothesis_text, evidence_summary,
        cross_domain_insights or [], prior_hypotheses or [],
    )


async def _llm_score(
    hypothesis_text: str,
    question: str,
    evidence_summary: str,
    cross_domain_insights: list[dict],
    prior_hypotheses: list[str],
) -> EvaluationRubric:
    prior_blurb = ""
    if prior_hypotheses:
        prior_blurb = "\n\nPrior hypotheses in this project (for novelty scoring):\n" + "\n".join(
            f"- {h[:200]}" for h in prior_hypotheses[:5]
        )
    cd_blurb = ""
    if cross_domain_insights:
        cd_blurb = "\n\nCross-domain insights used:\n" + "\n".join(
            f"- {i.get('source', '')} ↔ {i.get('target', '')} ({i.get('explanation', '')[:100]})"
            for i in cross_domain_insights[:3]
        )

    user_prompt = (
        f"Question: {question}\n\n"
        f"Evidence summary: {evidence_summary[:800]}\n\n"
        f"Hypothesis: {hypothesis_text[:800]}"
        f"{prior_blurb}{cd_blurb}"
    )

    async with httpx.AsyncClient(timeout=40) as client:
        resp = await client.post(
            f"{_settings.llm_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {_settings.llm_api_key}"},
            json={
                "model": _settings.llm_model,
                "messages": [
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

    start = content.find("{")
    end = content.rfind("}") + 1
    data = json.loads(content[start:end])

    dims = []
    for name in ("evidence_support", "specificity", "coherence", "novelty", "cross_domain"):
        entry = data.get(name, {})
        dims.append(ScoredDimension(
            name=name,
            score=max(0.0, min(1.0, float(entry.get("score", 0.5)))),
            reasoning=entry.get("reasoning", ""),
        ))
    return EvaluationRubric.from_dimensions(dims)


def _heuristic_score(
    hypothesis_text: str,
    evidence_summary: str,
    cross_domain_insights: list[dict],
    prior_hypotheses: list[str],
) -> EvaluationRubric:
    """Fast heuristic fallback — no LLM required."""
    # evidence_support: word overlap between evidence and hypothesis
    hyp_words = set(re.findall(r'\b\w{4,}\b', hypothesis_text.lower()))
    ev_words = set(re.findall(r'\b\w{4,}\b', evidence_summary.lower()))
    overlap = len(hyp_words & ev_words) / max(len(hyp_words), 1)
    evidence_score = min(1.0, overlap * 2.5)

    # specificity: sentence count + presence of numbers / technical terms
    sentences = [s.strip() for s in re.split(r'[.!?]', hypothesis_text) if s.strip()]
    has_numbers = bool(re.search(r'\d', hypothesis_text))
    specificity_score = min(1.0, (len(sentences) / 4) * 0.6 + (0.4 if has_numbers else 0.0))

    # coherence: proxy via sentence count (longer = more developed = more coherent)
    coherence_score = min(1.0, len(sentences) / 6)

    # novelty: if no prior, default to 0.7; else low score if very similar length
    if not prior_hypotheses:
        novelty_score = 0.7
    else:
        avg_len = sum(len(h) for h in prior_hypotheses) / len(prior_hypotheses)
        novelty_score = min(1.0, abs(len(hypothesis_text) - avg_len) / max(avg_len, 1))

    # cross_domain: non-zero only if insights were provided
    cross_domain_score = 0.6 if cross_domain_insights else 0.5

    dims = [
        ScoredDimension("evidence_support", round(evidence_score, 3), "word-overlap heuristic"),
        ScoredDimension("specificity", round(specificity_score, 3), "sentence/number heuristic"),
        ScoredDimension("coherence", round(coherence_score, 3), "sentence-count heuristic"),
        ScoredDimension("novelty", round(novelty_score, 3), "length-diff heuristic"),
        ScoredDimension("cross_domain", round(cross_domain_score, 3), "insight-presence heuristic"),
    ]
    return EvaluationRubric.from_dimensions(dims)
