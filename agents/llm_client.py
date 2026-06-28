"""Shared async LLM caller used by all pipeline steps and intelligence modules."""
import httpx

try:
    from app.config import settings as _settings
except ImportError:
    _settings = None


def auth_headers(base_url: str, api_key: str) -> dict:
    """Build request headers for an OpenAI-compatible endpoint. OpenRouter also
    wants HTTP-Referer / X-Title for ranking + free-tier acceptance; these are
    harmless for other providers."""
    headers = {"Authorization": f"Bearer {api_key}"}
    if "openrouter" in base_url:
        headers["HTTP-Referer"] = "https://huggingface.co/spaces/Aungnue546/universal-intelligence-lab"
        headers["X-Title"] = "Universal Intelligence Lab"
    return headers


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
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers=auth_headers(base_url, api_key),
                json={"model": model, "messages": messages, "temperature": temperature},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    except Exception:  # noqa: BLE001 — callers treat None as "no LLM" and fall back
        return None


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
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{base_url}/chat/completions",
                headers=auth_headers(base_url, api_key),
                json={"model": model, "messages": messages, "temperature": temperature},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    except Exception:  # noqa: BLE001 — callers treat None as "no LLM" and fall back
        return None
