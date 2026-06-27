from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.routers.auth import get_current_user
from app.schemas.tool import ToolInvokeRequest, ToolResultOut, ToolSpecOut

_root = str(Path(__file__).resolve().parents[4])
if _root not in sys.path:
    sys.path.insert(0, _root)

import tools.builtin_tools  # noqa: F401 — triggers auto-registration
from tools.tool_registry import call_tool, list_tools

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=list[ToolSpecOut])
async def get_tools():
    """Public tool catalog — no auth required."""
    return [
        ToolSpecOut(
            name=t.name,
            description=t.description,
            category=t.category,
            input_schema=t.input_schema,
        )
        for t in list_tools()
    ]


@router.post("/{tool_name}/invoke", response_model=ToolResultOut)
async def invoke_tool(
    tool_name: str,
    body: ToolInvokeRequest,
    _current_user=Depends(get_current_user),
):
    result = await call_tool(tool_name, body.args)
    if not result.success and result.error and "not found" in result.error:
        raise HTTPException(status_code=404, detail=result.error)
    return ToolResultOut(
        tool_name=result.tool_name,
        success=result.success,
        output=result.output,
        error=result.error,
        elapsed_ms=result.elapsed_ms,
    )
