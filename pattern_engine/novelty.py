"""novelty — measure how novel a candidate hypothesis or pattern is."""
from __future__ import annotations


async def score_novelty(
    hypothesis_text: str,
    prior_hypotheses: list[str],
    project_id: str,
) -> float:
    """Return a novelty score between 0.0 (duplicate) and 1.0 (fully novel).

    Uses embedding cosine similarity when the embedder is available;
    falls back to token-overlap Jaccard distance.
    """
    if not prior_hypotheses:
        return 1.0

    try:
        from memory.embedder import embed
        h_vec = embed(hypothesis_text)
        sims = [_cosine(h_vec, embed(p)) for p in prior_hypotheses]
        max_sim = max(sims) if sims else 0.0
        return round(1.0 - max_sim, 4)
    except Exception:
        return _jaccard_novelty(hypothesis_text, prior_hypotheses)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x ** 2 for x in a) ** 0.5
    mag_b = sum(x ** 2 for x in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _jaccard_novelty(text: str, priors: list[str]) -> float:
    tokens = set(text.lower().split())
    if not tokens:
        return 0.5
    max_overlap = max(
        len(tokens & set(p.lower().split())) / max(len(tokens | set(p.lower().split())), 1)
        for p in priors
    )
    return round(1.0 - max_overlap, 4)
