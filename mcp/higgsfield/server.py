"""
Higgsfield AI MCP Server

Exposes Higgsfield AI video-generation as MCP tools inside Claude Code.
Set HIGGSFIELD_API_KEY before running.
"""
from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from typing import Annotated, Optional
from mcp.server.fastmcp import FastMCP

from client import HiggsFieldClient, HiggsFieldError
from models import AspectRatio, CameraMotion, VideoModel

mcp = FastMCP(
    "Higgsfield AI",
    instructions="Generate and manage AI videos with Higgsfield AI. Requires HIGGSFIELD_API_KEY.",
)


def _client() -> HiggsFieldClient:
    return HiggsFieldClient()


def _fmt(g) -> str:
    lines = [f"ID:        {g.id}", f"Status:    {g.status}"]
    if g.prompt:       lines.append(f"Prompt:    {g.prompt[:120]}")
    if g.model:        lines.append(f"Model:     {g.model}")
    if g.aspect_ratio: lines.append(f"Ratio:     {g.aspect_ratio}")
    if g.duration:     lines.append(f"Duration:  {g.duration}s")
    if g.camera_motion:lines.append(f"Camera:    {g.camera_motion}")
    if g.video_url:    lines.append(f"Video URL: {g.video_url}")
    if g.thumbnail_url:lines.append(f"Thumbnail: {g.thumbnail_url}")
    if g.created_at:   lines.append(f"Created:   {g.created_at}")
    if g.error:        lines.append(f"Error:     {g.error}")
    return "\n".join(lines)


@mcp.tool()
async def generate_video(
    prompt: Annotated[str, "Text description of the video to generate"],
    model: Annotated[str, "Model: higgsfield-1 | diffusion-1"] = "higgsfield-1",
    aspect_ratio: Annotated[str, "Aspect ratio: 16:9 | 9:16 | 1:1"] = "16:9",
    duration: Annotated[int, "Duration in seconds: 4 | 6 | 8"] = 4,
    camera_motion: Annotated[str, "Camera movement: static | pan_left | pan_right | tilt_up | tilt_down | zoom_in | zoom_out | orbit_left | orbit_right | crane_up | crane_down | dolly_in | dolly_out"] = "static",
    image_url: Annotated[Optional[str], "Starting image URL for image-to-video (optional)"] = None,
    negative_prompt: Annotated[Optional[str], "Things to avoid in the video (optional)"] = None,
    seed: Annotated[Optional[int], "Random seed for reproducibility (optional)"] = None,
) -> str:
    """Generate an AI video with Higgsfield AI (text-to-video or image-to-video)."""
    try:
        gen = await _client().generate_video(
            prompt=prompt, model=model, aspect_ratio=aspect_ratio,
            duration=duration, camera_motion=camera_motion,
            image_url=image_url, negative_prompt=negative_prompt, seed=seed,
        )
        return "Video generation submitted!\n\n" + _fmt(gen) + "\n\nUse get_video_status to check progress."
    except (HiggsFieldError, ValueError, Exception) as exc:
        return f"Error: {exc}"


@mcp.tool()
async def get_video_status(
    generation_id: Annotated[str, "Generation ID returned by generate_video"],
) -> str:
    """Check the status of a Higgsfield video generation and get the download URL when ready."""
    try:
        gen = await _client().get_generation(generation_id)
        result = _fmt(gen)
        if gen.status == "completed" and gen.video_url:
            result += "\n\nReady! Download from the Video URL above."
        elif gen.status == "failed":
            result += "\n\nGeneration failed. Try a new request."
        else:
            result += "\n\nStill processing — check again shortly."
        return result
    except (HiggsFieldError, ValueError, Exception) as exc:
        return f"Error: {exc}"


@mcp.tool()
async def list_videos(
    page: Annotated[int, "Page number (1-based)"] = 1,
    limit: Annotated[int, "Results per page (max 50)"] = 10,
) -> str:
    """List past Higgsfield video generations for your account."""
    try:
        result = await _client().list_generations(page=page, limit=min(limit, 50))
        if not result.items:
            return "No generations found."
        lines = [f"Showing {len(result.items)} of {result.total} (page {result.page}):\n"]
        for i, g in enumerate(result.items, 1):
            lines += [f"--- [{i}] ---", _fmt(g), ""]
        return "\n".join(lines).strip()
    except (HiggsFieldError, ValueError, Exception) as exc:
        return f"Error: {exc}"


@mcp.tool()
async def delete_video(
    generation_id: Annotated[str, "Generation ID to delete"],
) -> str:
    """Permanently delete a Higgsfield video generation."""
    try:
        res = await _client().delete_generation(generation_id)
        return f"Deleted {generation_id}: {res.get('message') or 'OK'}"
    except (HiggsFieldError, ValueError, Exception) as exc:
        return f"Error: {exc}"


@mcp.tool()
async def get_account_info() -> str:
    """Return Higgsfield account details and usage quotas."""
    try:
        data = await _client().get_account()
        return "\n".join(f"{k.replace('_',' ').title()}: {v}" for k, v in data.items()) or "No data returned."
    except (HiggsFieldError, ValueError, Exception) as exc:
        return f"Error: {exc}"


@mcp.tool()
async def list_camera_motions() -> str:
    """List all available Higgsfield camera movement presets."""
    items = {
        "static": "Fixed shot — no movement",
        "pan_left": "Pan smoothly left",
        "pan_right": "Pan smoothly right",
        "tilt_up": "Tilt upward",
        "tilt_down": "Tilt downward",
        "zoom_in": "Zoom toward subject",
        "zoom_out": "Zoom away from subject",
        "orbit_left": "Orbit subject counter-clockwise",
        "orbit_right": "Orbit subject clockwise",
        "crane_up": "Rise vertically",
        "crane_down": "Descend vertically",
        "dolly_in": "Dolly toward subject",
        "dolly_out": "Dolly away from subject",
    }
    return "Camera motions:\n" + "\n".join(f"  {k:<16} — {v}" for k, v in items.items())


@mcp.tool()
async def list_models() -> str:
    """List available Higgsfield AI video generation models."""
    return (
        "Models:\n"
        "  higgsfield-1  — Flagship cinematic model. Best quality (recommended).\n"
        "  diffusion-1   — Fast diffusion model. Lower latency for quick tests."
    )


if __name__ == "__main__":
    mcp.run()
