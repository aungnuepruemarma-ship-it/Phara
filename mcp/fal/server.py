"""
fal.ai MCP Server

Exposes fal.ai AI model inference as MCP tools inside Claude Code.
Set FAL_KEY before running.

Covered capabilities:
  - Image generation  (FLUX Schnell, FLUX Dev, FLUX Pro, SDXL)
  - Video generation  (Kling, MiniMax, Luma Dream Machine)
  - Audio generation  (Stable Audio)
  - Speech-to-text    (Whisper)
  - Image editing     (background removal, upscaling, face swap)
  - Run any model     (fal_run_model — full access to all fal.ai endpoints)
"""
from __future__ import annotations

import json
import os
from typing import Annotated, Any, Optional

import fal_client
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "fal.ai",
    instructions=(
        "Run AI models on fal.ai: image generation, video generation, "
        "audio, transcription, image editing, and more. Requires FAL_KEY."
    ),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_key() -> None:
    if not os.environ.get("FAL_KEY"):
        raise ValueError("FAL_KEY environment variable is not set.")


def _pretty(result: Any) -> str:
    if isinstance(result, dict):
        return json.dumps(result, indent=2)
    return str(result)


async def _run(model_id: str, args: dict) -> Any:
    _check_key()
    handler = await fal_client.submit_async(model_id, arguments=args)
    return await handler.get()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def fal_run_model(
    model_id: Annotated[str, "fal.ai model ID, e.g. 'fal-ai/flux/schnell' or 'fal-ai/kling-video'"],
    arguments: Annotated[str, "JSON string of model input arguments, e.g. '{\"prompt\": \"a sunset\"}'"],
) -> str:
    """
    Run ANY fal.ai model with arbitrary arguments.

    Use this for full flexibility — any model on fal.ai can be invoked here.
    Returns the raw model output as JSON.
    """
    try:
        _check_key()
        args = json.loads(arguments)
        result = await _run(model_id, args)
        return _pretty(result)
    except json.JSONDecodeError as exc:
        return f"Invalid JSON in arguments: {exc}"
    except (ValueError, Exception) as exc:
        return f"Error: {exc}"


@mcp.tool()
async def generate_image(
    prompt: Annotated[str, "Text description of the image to generate"],
    model: Annotated[
        str,
        "Model to use: flux-schnell (fastest) | flux-dev | flux-pro | sdxl",
    ] = "flux-schnell",
    image_size: Annotated[
        str,
        "Output size: square_hd | square | portrait_4_3 | portrait_16_9 | landscape_4_3 | landscape_16_9",
    ] = "landscape_16_9",
    num_images: Annotated[int, "Number of images to generate (1–4)"] = 1,
    negative_prompt: Annotated[Optional[str], "Things to avoid in the image (optional)"] = None,
    seed: Annotated[Optional[int], "Random seed for reproducibility (optional)"] = None,
) -> str:
    """
    Generate images using fal.ai FLUX or SDXL models.

    Returns image URLs from fal.ai's CDN ready to view or download.
    """
    model_map = {
        "flux-schnell": "fal-ai/flux/schnell",
        "flux-dev":     "fal-ai/flux/dev",
        "flux-pro":     "fal-ai/flux-pro",
        "sdxl":         "fal-ai/fast-sdxl",
    }
    try:
        _check_key()
        fal_model = model_map.get(model, f"fal-ai/{model}")
        args: dict[str, Any] = {
            "prompt": prompt,
            "image_size": image_size,
            "num_images": min(num_images, 4),
        }
        if negative_prompt:
            args["negative_prompt"] = negative_prompt
        if seed is not None:
            args["seed"] = seed

        result = await _run(fal_model, args)

        images = result.get("images") or []
        if not images:
            return f"No images returned.\n\nRaw response:\n{_pretty(result)}"

        lines = [f"Generated {len(images)} image(s) with {fal_model}:\n"]
        for i, img in enumerate(images, 1):
            url = img.get("url", img) if isinstance(img, dict) else img
            width = img.get("width", "") if isinstance(img, dict) else ""
            height = img.get("height", "") if isinstance(img, dict) else ""
            size_str = f" ({width}x{height})" if width and height else ""
            lines.append(f"[{i}] {url}{size_str}")

        seed_out = result.get("seed")
        if seed_out:
            lines.append(f"\nSeed: {seed_out}")
        return "\n".join(lines)
    except (ValueError, Exception) as exc:
        return f"Error: {exc}"


@mcp.tool()
async def generate_video(
    prompt: Annotated[str, "Text description of the video to generate"],
    model: Annotated[
        str,
        "Model: kling (default) | minimax | luma | wan",
    ] = "kling",
    duration: Annotated[
        str,
        "Video duration: '5' or '10' seconds (model-dependent)",
    ] = "5",
    aspect_ratio: Annotated[str, "Aspect ratio: 16:9 | 9:16 | 1:1"] = "16:9",
    image_url: Annotated[Optional[str], "Starting image URL for image-to-video (optional)"] = None,
) -> str:
    """
    Generate videos using fal.ai video models (Kling, MiniMax, Luma, Wan).

    Returns a video URL once generation is complete.
    Video generation typically takes 30–120 seconds.
    """
    model_map = {
        "kling":   "fal-ai/kling-video/v1.6/standard/text-to-video",
        "minimax": "fal-ai/minimax-video",
        "luma":    "fal-ai/luma-dream-machine",
        "wan":     "fal-ai/wan-t2v-1.3b",
    }
    try:
        _check_key()
        fal_model = model_map.get(model, f"fal-ai/{model}")
        args: dict[str, Any] = {
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
        }
        if image_url:
            args["image_url"] = image_url
            # Switch to image-to-video endpoint for kling
            if model == "kling":
                fal_model = "fal-ai/kling-video/v1.6/standard/image-to-video"

        result = await _run(fal_model, args)

        video = result.get("video") or {}
        url = video.get("url") if isinstance(video, dict) else result.get("video_url", "")
        if not url:
            return f"No video URL in response.\n\nRaw:\n{_pretty(result)}"

        lines = [f"Video generated with {fal_model}:", f"URL: {url}"]
        if isinstance(video, dict):
            if video.get("duration"):
                lines.append(f"Duration: {video['duration']}s")
            if video.get("width") and video.get("height"):
                lines.append(f"Size: {video['width']}x{video['height']}")
        return "\n".join(lines)
    except (ValueError, Exception) as exc:
        return f"Error: {exc}"


@mcp.tool()
async def transcribe_audio(
    audio_url: Annotated[str, "URL of audio file to transcribe (mp3, wav, m4a, etc.)"],
    language: Annotated[Optional[str], "Language code, e.g. 'en', 'es', 'fr' (auto-detected if omitted)"] = None,
    task: Annotated[str, "Task: transcribe | translate (translate converts to English)"] = "transcribe",
) -> str:
    """
    Transcribe or translate audio using Whisper on fal.ai.

    Supports 99+ languages. 'translate' converts speech in any language to English text.
    """
    try:
        _check_key()
        args: dict[str, Any] = {"audio_url": audio_url, "task": task}
        if language:
            args["language"] = language

        result = await _run("fal-ai/whisper", args)

        text = result.get("text") or ""
        chunks = result.get("chunks") or []
        lines = []
        if text:
            lines.append(f"Transcription:\n{text}")
        if chunks:
            lines.append(f"\nSegments ({len(chunks)} total):")
            for c in chunks[:10]:
                ts = c.get("timestamp", [])
                ts_str = f"[{ts[0]:.1f}s – {ts[1]:.1f}s]" if len(ts) == 2 else ""
                lines.append(f"  {ts_str} {c.get('text', '').strip()}")
            if len(chunks) > 10:
                lines.append(f"  ... and {len(chunks) - 10} more segments")
        return "\n".join(lines) if lines else _pretty(result)
    except (ValueError, Exception) as exc:
        return f"Error: {exc}"


@mcp.tool()
async def generate_audio(
    prompt: Annotated[str, "Text description of the audio/music to generate"],
    duration: Annotated[float, "Duration in seconds (up to 47s)"] = 15.0,
    steps: Annotated[int, "Inference steps — higher = better quality (20–200)"] = 100,
) -> str:
    """
    Generate music or sound effects from a text prompt using Stable Audio on fal.ai.

    Returns a URL to the generated audio file.
    """
    try:
        _check_key()
        result = await _run("fal-ai/stable-audio", {
            "prompt": prompt,
            "seconds_total": min(duration, 47.0),
            "steps": min(steps, 200),
        })
        url = (result.get("audio_file") or {}).get("url") or result.get("audio_url", "")
        if not url:
            return f"No audio URL in response.\n\nRaw:\n{_pretty(result)}"
        return f"Audio generated:\nURL: {url}\nPrompt: {prompt}"
    except (ValueError, Exception) as exc:
        return f"Error: {exc}"


@mcp.tool()
async def remove_background(
    image_url: Annotated[str, "URL of the image to remove background from"],
) -> str:
    """
    Remove the background from an image using fal.ai.

    Returns a URL to the processed image with a transparent background (PNG).
    """
    try:
        _check_key()
        result = await _run("fal-ai/birefnet", {"image_url": image_url})
        url = (result.get("image") or {}).get("url") or result.get("image_url", "")
        if not url:
            return f"No image URL in response.\n\nRaw:\n{_pretty(result)}"
        return f"Background removed:\nURL: {url}"
    except (ValueError, Exception) as exc:
        return f"Error: {exc}"


@mcp.tool()
async def upscale_image(
    image_url: Annotated[str, "URL of image to upscale"],
    scale: Annotated[int, "Upscale factor: 2 | 4"] = 4,
) -> str:
    """
    Upscale an image by 2x or 4x using the Real-ESRGAN model on fal.ai.

    Returns a URL to the upscaled image.
    """
    try:
        _check_key()
        result = await _run("fal-ai/esrgan", {
            "image_url": image_url,
            "scale": scale,
        })
        url = (result.get("image") or {}).get("url") or result.get("image_url", "")
        if not url:
            return f"No image URL in response.\n\nRaw:\n{_pretty(result)}"
        return f"Image upscaled {scale}x:\nURL: {url}"
    except (ValueError, Exception) as exc:
        return f"Error: {exc}"


@mcp.tool()
async def list_popular_models() -> str:
    """
    List popular fal.ai models by category with their model IDs.
    """
    categories = {
        "Image Generation": [
            ("fal-ai/flux/schnell",  "FLUX Schnell — fastest, great quality"),
            ("fal-ai/flux/dev",      "FLUX Dev — high quality, slower"),
            ("fal-ai/flux-pro",      "FLUX Pro — best quality"),
            ("fal-ai/fast-sdxl",     "Stable Diffusion XL — fast"),
            ("fal-ai/aura-flow",     "AuraFlow — open model"),
        ],
        "Video Generation": [
            ("fal-ai/kling-video/v1.6/standard/text-to-video", "Kling 1.6 — cinematic quality"),
            ("fal-ai/minimax-video",         "MiniMax Video"),
            ("fal-ai/luma-dream-machine",    "Luma Dream Machine"),
            ("fal-ai/wan-t2v-1.3b",         "Wan T2V — fast"),
        ],
        "Audio": [
            ("fal-ai/stable-audio",  "Stable Audio — music & sound generation"),
            ("fal-ai/whisper",       "Whisper — speech-to-text (99+ languages)"),
        ],
        "Image Editing": [
            ("fal-ai/birefnet",      "BiRefNet — background removal"),
            ("fal-ai/esrgan",        "Real-ESRGAN — image upscaling 2x/4x"),
            ("fal-ai/face-swap",     "Face Swap"),
            ("fal-ai/inpaint",       "Inpainting — fill masked regions"),
        ],
    }
    lines = ["Popular fal.ai models (use model IDs with fal_run_model):\n"]
    for category, models in categories.items():
        lines.append(f"## {category}")
        for model_id, desc in models:
            lines.append(f"  {model_id}")
            lines.append(f"    {desc}")
        lines.append("")
    lines.append("Browse all models at: https://fal.ai/models")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
