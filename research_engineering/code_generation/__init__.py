"""code_generation — produce runnable code artifacts from accepted hypotheses.

SAFETY: always call research_engineering.require_accepted(review_status) first.
"""
from __future__ import annotations


async def generate_prototype(
    hypothesis_text: str,
    review_status: str,
    language: str = "python",
) -> dict:
    """Generate a minimal prototype implementation for an accepted hypothesis.

    Returns {"code": str, "language": str, "notes": str}.
    Raises ValueError if the hypothesis has not been accepted.
    """
    from research_engineering import require_accepted
    require_accepted(review_status)

    # LLM-based code generation
    try:
        from app.config import settings
        import httpx

        if not settings.llm_api_key:
            return _scaffold(hypothesis_text, language)

        prompt = (
            f"Write a minimal {language} prototype that implements or tests the following "
            f"research hypothesis. Include inline comments explaining the key design choices. "
            f"Keep it under 80 lines.\n\nHypothesis:\n{hypothesis_text}"
        )
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                },
            )
            resp.raise_for_status()
            code = resp.json()["choices"][0]["message"]["content"]
        return {"code": code, "language": language, "notes": "LLM-generated prototype"}
    except Exception:
        return _scaffold(hypothesis_text, language)


def _scaffold(hypothesis_text: str, language: str) -> dict:
    code = (
        f"# Prototype for hypothesis:\n"
        f"# {hypothesis_text[:200]}\n\n"
        f"# TODO: implement the key mechanism described above\n\n"
        f"def hypothesis_test():\n"
        f"    raise NotImplementedError('Prototype not yet implemented')\n\n"
        f"if __name__ == '__main__':\n"
        f"    hypothesis_test()\n"
    )
    return {"code": code, "language": language, "notes": "Scaffold — LLM unavailable"}
