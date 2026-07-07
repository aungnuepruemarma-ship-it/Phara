"""Resilient OpenRouter chat client. Stdlib only (urllib).

chat() retries transient failures (429/5xx) per model with short backoff and
falls back across the free-model chain; returns None when no key is configured
or every attempt failed — callers must degrade gracefully on None.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from . import config

_RETRY_STATUSES = {429, 500, 502, 503, 504}
_BACKOFFS = (1.0, 3.0)

_HEADERS_EXTRA = {
    "HTTP-Referer": "https://github.com/sciloop",
    "X-Title": "SciLoop",
}


def _post(model: str, messages: list[dict], temperature: float, timeout: float):
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }).encode()
    req = urllib.request.Request(
        config.OPENROUTER_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            **_HEADERS_EXTRA,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return -1, None  # network error / timeout


def chat(messages: list[dict], temperature: float = 0.4, timeout: float = 90) -> str | None:
    """Call the LLM with retry + model fallback. None => unavailable/failed."""
    if not config.llm_available():
        return None
    for model in config.model_chain():
        for attempt in range(len(_BACKOFFS) + 1):
            status, data = _post(model, messages, temperature, timeout)
            if status == 200 and data:
                try:
                    text = data["choices"][0]["message"]["content"]
                    if text:
                        return text
                except (KeyError, IndexError, TypeError):
                    pass
                break  # 200 but bad shape -> next model
            if (status in _RETRY_STATUSES or status == -1) and attempt < len(_BACKOFFS):
                time.sleep(_BACKOFFS[attempt])
                continue
            break  # 404 (retired model) / auth error / exhausted -> next model
    return None


def chat_json(messages: list[dict], temperature: float = 0.3, timeout: float = 90) -> dict | list | None:
    """chat() + extract the first JSON object/array from the reply."""
    text = chat(messages, temperature=temperature, timeout=timeout)
    if not text:
        return None
    for open_c, close_c in (("{", "}"), ("[", "]")):
        start, end = text.find(open_c), text.rfind(close_c) + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                continue
    return None
