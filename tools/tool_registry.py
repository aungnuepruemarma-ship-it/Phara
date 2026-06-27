"""
Tool registry — central catalog of callable tools.

Usage:
    from tools.tool_registry import register_tool, call_tool, list_tools
    import tools.builtin_tools  # triggers auto-registration
"""
from __future__ import annotations

import time
from typing import Any, Callable

from tools.tool_spec import ToolResult, ToolSpec

TOOL_REGISTRY: dict[str, ToolSpec] = {}
_TOOL_FNS: dict[str, Callable] = {}


def register_tool(spec: ToolSpec, fn: Callable) -> None:
    TOOL_REGISTRY[spec.name] = spec
    _TOOL_FNS[spec.name] = fn


def get_tool_spec(name: str) -> ToolSpec | None:
    return TOOL_REGISTRY.get(name)


def list_tools() -> list[ToolSpec]:
    return list(TOOL_REGISTRY.values())


async def call_tool(name: str, args: dict) -> ToolResult:
    """Invoke a registered tool by name. Returns ToolResult(success=False) on any error."""
    fn = _TOOL_FNS.get(name)
    if fn is None:
        return ToolResult(tool_name=name, success=False, output=None, error=f"Tool '{name}' not found")

    t0 = time.monotonic()
    try:
        output = await fn(**args)
        elapsed = (time.monotonic() - t0) * 1000
        return ToolResult(tool_name=name, success=True, output=output, elapsed_ms=round(elapsed, 1))
    except Exception as exc:
        elapsed = (time.monotonic() - t0) * 1000
        return ToolResult(tool_name=name, success=False, output=None, error=str(exc)[:500], elapsed_ms=round(elapsed, 1))
