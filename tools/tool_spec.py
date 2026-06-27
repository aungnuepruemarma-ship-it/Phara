"""
ToolSpec and ToolResult — MCP-compatible tool schema primitives.

ToolSpec mirrors the MCP tool definition shape (name, description, inputSchema)
so it can later be bridged to a real MCP server with no schema changes.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolSpec:
    name: str
    description: str
    category: str       # "research" | "memory" | "analysis" | "utility"
    input_schema: dict  # JSON schema {"type":"object","properties":{...},"required":[...]}


@dataclass
class ToolResult:
    tool_name: str
    success: bool
    output: Any         # list | dict | str | None
    error: str | None = None
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "elapsed_ms": self.elapsed_ms,
        }
