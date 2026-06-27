from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ToolSpecOut(BaseModel):
    name: str
    description: str
    category: str
    input_schema: dict


class ToolInvokeRequest(BaseModel):
    args: dict = {}


class ToolResultOut(BaseModel):
    tool_name: str
    success: bool
    output: Any
    error: str | None = None
    elapsed_ms: float = 0.0
