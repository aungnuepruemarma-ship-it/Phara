"""Shared async LLM caller used by all pipeline steps and intelligence modules."""
import httpx

try:
    from app.config import settings as _settings
except ImportError:
    _settings = None


async def acall_llm(
    messages: list[dict],
    temperature: float = 0.7,
    timeout: float = 90,
) -> str | None:
    """Call the configured LLM and return the response text, or None if no LLM is configured."""
    creds = _settings.llm_credentials if _settings else None
    if not creds:
        return None
    base_url, api_key, model = creds
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": messages, "temperature": temperature},
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


def call_llm(
    messages: list[dict],
    temperature: float = 0.7,
    timeout: float = 90,
) -> str | None:
    """Synchronous variant of acall_llm."""
    creds = _settings.llm_credentials if _settings else None
    if not creds:
        return None
    base_url, api_key, model = creds
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": messages, "temperature": temperature},
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
