"""Shared LLM caller used by all pipeline steps, agents, and intelligence modules.

Provides a resilient OpenAI-compatible chat caller that, on OpenRouter, retries
transient rate limits (429/5xx) and falls back across several free models so a
real completion comes back even when one free model is busy or retired.
"""
import asyncio
import time

import httpx

try:
    from app.config import settings as _settings
except ImportError:
    _settings = None

# Statuses worth retrying on the same model (transient upstream issues).
_RETRY_STATUSES = {429, 500, 502, 503, 504}
_BACKOFFS = (1.0, 3.0)  # seconds between retries (==> up to 3 attempts/model)


def auth_headers(base_url: str, api_key: str) -> dict:
    """Build request headers for an OpenAI-compatible endpoint. OpenRouter also
    wants HTTP-Referer / X-Title for ranking + free-tier acceptance; these are
    harmless for other providers."""
    headers = {"Authorization": f"Bearer {api_key}"}
    if "openrouter" in base_url:
        headers["HTTP-Referer"] = "https://huggingface.co/spaces/Aungnue546/universal-intelligence-lab"
        headers["X-Title"] = "Universal Intelligence Lab"
    return headers


def _model_chain(base_url: str, primary: str) -> list[str]:
    """Primary model first, then OpenRouter free-model fallbacks (deduped).
    Non-OpenRouter providers just use their single configured model."""
    if "openrouter" not in base_url or _settings is None:
        return [primary]
    raw = getattr(_settings, "openrouter_fallback_models", "") or ""
    chain = [primary] + [m.strip() for m in raw.split(",") if m.strip()]
    seen: set[str] = set()
    out: list[str] = []
    for m in chain:
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    return out


def _extract(payload: dict) -> str | None:
    try:
        return payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None


async def resilient_chat(
    messages: list[dict],
    temperature: float = 0.7,
    timeout: float = 90,
) -> str | None:
    """Call the configured LLM with retry + free-model fallback. Returns the
    response text, or None when no LLM is configured or every attempt failed."""
    creds = _settings.llm_credentials if _settings else None
    if not creds:
        return None
    base_url, api_key, primary = creds
    url = f"{base_url}/chat/completions"
    headers = auth_headers(base_url, api_key)

    async with httpx.AsyncClient(timeout=timeout) as client:
        for model in _model_chain(base_url, primary):
            for attempt in range(len(_BACKOFFS) + 1):
                try:
                    resp = await client.post(
                        url, headers=headers,
                        json={"model": model, "messages": messages, "temperature": temperature},
                    )
                except Exception:  # noqa: BLE001 — network error: retry, then next model
                    if attempt < len(_BACKOFFS):
                        await asyncio.sleep(_BACKOFFS[attempt])
                        continue
                    break
                if resp.status_code == 200:
                    text = _extract(resp.json())
                    if text:
                        return text
                    break  # 200 but unexpected shape → try next model
                if resp.status_code in _RETRY_STATUSES and attempt < len(_BACKOFFS):
                    await asyncio.sleep(_BACKOFFS[attempt])
                    continue
                # 404 (retired/unavailable) or exhausted retries → next model
                break
    return None


def resilient_chat_sync(
    messages: list[dict],
    temperature: float = 0.7,
    timeout: float = 90,
) -> str | None:
    """Synchronous mirror of resilient_chat."""
    creds = _settings.llm_credentials if _settings else None
    if not creds:
        return None
    base_url, api_key, primary = creds
    url = f"{base_url}/chat/completions"
    headers = auth_headers(base_url, api_key)

    with httpx.Client(timeout=timeout) as client:
        for model in _model_chain(base_url, primary):
            for attempt in range(len(_BACKOFFS) + 1):
                try:
                    resp = client.post(
                        url, headers=headers,
                        json={"model": model, "messages": messages, "temperature": temperature},
                    )
                except Exception:  # noqa: BLE001
                    if attempt < len(_BACKOFFS):
                        time.sleep(_BACKOFFS[attempt])
                        continue
                    break
                if resp.status_code == 200:
                    text = _extract(resp.json())
                    if text:
                        return text
                    break
                if resp.status_code in _RETRY_STATUSES and attempt < len(_BACKOFFS):
                    time.sleep(_BACKOFFS[attempt])
                    continue
                break
    return None


# Backwards-compatible names used across the codebase.
async def acall_llm(messages: list[dict], temperature: float = 0.7, timeout: float = 90) -> str | None:
    return await resilient_chat(messages, temperature=temperature, timeout=timeout)


def call_llm(messages: list[dict], temperature: float = 0.7, timeout: float = 90) -> str | None:
    return resilient_chat_sync(messages, temperature=temperature, timeout=timeout)
