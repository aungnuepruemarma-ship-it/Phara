"""
Higgsfield AI MCP Server

Exposes Higgsfield AI video-generation capabilities as MCP tools so any
MCP-compatible client (Claude Desktop, Cursor, Windsurf, …) can generate,
inspect, and manage AI videos.

Usage
-----
1. Set the HIGGSFIELD_API_KEY environment variable.
2. Run:  python -m mcp.higgsfield.server
   or:   uvx --from . higgsfield-mcp

Claude Desktop config (claude_desktop_config.json)
---------------------------------------------------
{
  "mcpServers": {
    "higgsfield": {
      "command": "python",
      "args": ["-m", "mcp.higgsfield.server"],
      "env": { "HIGGSFIELD_API_KEY": "YOUR_KEY_HERE" }
    }
  }
}
"""
from __future__ import annotations

import asyncio
import os
from typing import Annotated, Optional

from mcp.server.fastmcp import FastMCP

from .client import HiggsFieldClient, HiggsFieldError
from .models import AspectRatio, CameraMotion, VideoModel

# ---------------------------------------------------------------------------
# Server bootstrap
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "Higgsfield AI",
    instructions=(
        "Tools for generating, inspecting, and managing AI videos using "
        "the Higgsfield AI platform. Set HIGGSFIELD_API_KEY before use."
    ),
)


def _client() -> HiggsFieldClient:
    """Return a configured Higgsfield client (fails fast if no key set)."""
    return HiggsFieldClient()


# ---------------------------------------------------------------------------
# Tool helpers
# ---------------------------------------------------------------------------

def _fmt_generation(g) -> str:
    lines = [
        f"ID:           {g.id}",
        f"Status:       {g.status}",
    ]
    if g.prompt:
        lines.append(f"Prompt:       {g.prompt[:120]}")
    if g.model:
        lines.append(f"Model:        {g.model}")
    if g.aspect_ratio:
        lines.append(f"Aspect ratio: {g.aspect_ratio}")
    if g.duration:
        lines.append(f"Duration:     {g.duration}s")
    if g.camera_motion:
        lines.append(f"Camera:       {g.camera_motion}")
    if g.video_url:
        lines.append(f"Video URL:    {g.video_url}")
    if g.thumbnail_url:
        lines.append(f"Thumbnail:    {g.thumbnail_url}")
    if g.created_at:
        lines.append(f"Created:      {g.created_at}")
    if g.completed_at:
        lines.append(f"Completed:    {g.completed_at}")
    if g.error:
        lines.append(f"Error:        {g.error}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def generate_video(
    prompt: Annotated[str, "Text description of the video to generate"],
    model: Annotated[
        str,
        f"Model to use. Options: {', '.join(m.value for m in VideoModel)}",
    ] = VideoModel.HIGGSFIELD_1,
    aspect_ratio: Annotated[
        str,
        f"Aspect ratio. Options: {', '.join(a.value for a in AspectRatio)}",
    ] = AspectRatio.LANDSCAPE,
    duration: Annotated[int, "Video duration in seconds (4, 6, or 8)"] = 4,
    camera_motion: Annotated[
        str,
        f"Camera movement preset. Options: {', '.join(c.value for c in CameraMotion)}",
    ] = CameraMotion.STATIC,
    image_url: Annotated[
        Optional[str],
        "URL of a starting image for image-to-video generation (optional)",
    ] = None,
    negative_prompt: Annotated[
        Optional[str],
        "Elements to avoid in the generated video (optional)",
    ] = None,
    seed: Annotated[
        Optional[int],
        "Random seed for reproducibility (optional)",
    ] = None,
) -> str:
    """
    Generate an AI video using Higgsfield AI.

    Submits a generation job and returns the job ID and initial status.
    Use `get_video_status` to poll until the video is ready and retrieve
    the download URL.

    Supports both text-to-video (prompt only) and image-to-video
    (prompt + image_url).
    """
    try:
        client = _client()
        gen = await client.generate_video(
            prompt=prompt,
            model=model,
            aspect_ratio=aspect_ratio,
            duration=duration,
            camera_motion=camera_motion,
            image_url=image_url,
            negative_prompt=negative_prompt,
            seed=seed,
        )
        return (
            "Video generation submitted successfully!\n\n"
            + _fmt_generation(gen)
            + "\n\nUse `get_video_status` with this ID to check progress."
        )
    except HiggsFieldError as exc:
        return f"Higgsfield API error ({exc.status_code}): {exc.detail}"
    except ValueError as exc:
        return f"Configuration error: {exc}"
    except Exception as exc:
        return f"Unexpected error: {exc}"


@mcp.tool()
async def get_video_status(
    generation_id: Annotated[str, "Generation ID returned by generate_video"],
) -> str:
    """
    Retrieve the current status of a Higgsfield video generation job.

    Returns status (pending / processing / completed / failed) and, once
    completed, the video download URL and thumbnail URL.
    """
    try:
        client = _client()
        gen = await client.get_generation(generation_id)
        result = _fmt_generation(gen)
        if gen.status == "completed" and gen.video_url:
            result += "\n\nThe video is ready! Use the Video URL above to download it."
        elif gen.status == "failed":
            result += "\n\nGeneration failed. Try submitting a new job with a different prompt."
        elif gen.status in ("pending", "processing"):
            result += "\n\nStill generating — check again in a few seconds."
        return result
    except HiggsFieldError as exc:
        return f"Higgsfield API error ({exc.status_code}): {exc.detail}"
    except ValueError as exc:
        return f"Configuration error: {exc}"
    except Exception as exc:
        return f"Unexpected error: {exc}"


@mcp.tool()
async def list_videos(
    page: Annotated[int, "Page number (1-based)"] = 1,
    limit: Annotated[int, "Results per page (max 50)"] = 10,
) -> str:
    """
    List past Higgsfield AI video generations for your account.

    Returns a paginated list with IDs, statuses, prompts, and video URLs.
    """
    try:
        client = _client()
        result = await client.list_generations(page=page, limit=min(limit, 50))
        if not result.items:
            return "No video generations found."

        lines = [
            f"Showing {len(result.items)} of {result.total} generation(s) "
            f"(page {result.page}):\n"
        ]
        for i, gen in enumerate(result.items, start=1):
            lines.append(f"--- [{i}] ---")
            lines.append(_fmt_generation(gen))
            lines.append("")
        return "\n".join(lines).strip()
    except HiggsFieldError as exc:
        return f"Higgsfield API error ({exc.status_code}): {exc.detail}"
    except ValueError as exc:
        return f"Configuration error: {exc}"
    except Exception as exc:
        return f"Unexpected error: {exc}"


@mcp.tool()
async def delete_video(
    generation_id: Annotated[str, "Generation ID to delete"],
) -> str:
    """
    Delete a Higgsfield video generation and its associated video file.

    This action is irreversible. The video URL will no longer be accessible.
    """
    try:
        client = _client()
        result = await client.delete_generation(generation_id)
        msg = result.get("message") or result.get("detail") or "Deleted successfully."
        return f"Generation {generation_id} deleted: {msg}"
    except HiggsFieldError as exc:
        return f"Higgsfield API error ({exc.status_code}): {exc.detail}"
    except ValueError as exc:
        return f"Configuration error: {exc}"
    except Exception as exc:
        return f"Unexpected error: {exc}"


@mcp.tool()
async def get_account_info() -> str:
    """
    Return Higgsfield account info including usage quotas and plan details.
    """
    try:
        client = _client()
        data = await client.get_account()
        lines = []
        for key, value in data.items():
            lines.append(f"{key.replace('_', ' ').title()}: {value}")
        return "\n".join(lines) if lines else "Account info retrieved (no fields returned)."
    except HiggsFieldError as exc:
        return f"Higgsfield API error ({exc.status_code}): {exc.detail}"
    except ValueError as exc:
        return f"Configuration error: {exc}"
    except Exception as exc:
        return f"Unexpected error: {exc}"


@mcp.tool()
async def list_camera_motions() -> str:
    """
    List all available camera motion presets for video generation.
    """
    descriptions = {
        CameraMotion.STATIC:      "No camera movement — fixed shot",
        CameraMotion.PAN_LEFT:    "Camera pans smoothly to the left",
        CameraMotion.PAN_RIGHT:   "Camera pans smoothly to the right",
        CameraMotion.TILT_UP:     "Camera tilts upward",
        CameraMotion.TILT_DOWN:   "Camera tilts downward",
        CameraMotion.ZOOM_IN:     "Camera zooms in toward the subject",
        CameraMotion.ZOOM_OUT:    "Camera zooms out from the subject",
        CameraMotion.ORBIT_LEFT:  "Camera orbits the subject counter-clockwise",
        CameraMotion.ORBIT_RIGHT: "Camera orbits the subject clockwise",
        CameraMotion.CRANE_UP:    "Camera cranes upward (vertical rise)",
        CameraMotion.CRANE_DOWN:  "Camera cranes downward (vertical descent)",
        CameraMotion.DOLLY_IN:    "Camera dollies toward the subject",
        CameraMotion.DOLLY_OUT:   "Camera dollies away from the subject",
    }
    lines = ["Available camera motions:\n"]
    for motion, desc in descriptions.items():
        lines.append(f"  {motion.value:<16} — {desc}")
    return "\n".join(lines)


@mcp.tool()
async def list_models() -> str:
    """
    List available Higgsfield AI video generation models.
    """
    info = {
        VideoModel.HIGGSFIELD_1: (
            "Higgsfield-1 — Flagship cinematic model. Best quality and "
            "prompt adherence. Recommended for most use cases."
        ),
        VideoModel.DIFFUSION_1: (
            "Diffusion-1 — Fast diffusion-based model. Lower latency, "
            "good for quick prototyping."
        ),
    }
    lines = ["Available models:\n"]
    for model, desc in info.items():
        lines.append(f"  {model.value}")
        lines.append(f"    {desc}\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
