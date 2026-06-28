"""Async HTTP client for the Higgsfield AI REST API."""
from __future__ import annotations

import os
from typing import Any, Optional

import httpx

from .models import (
    AspectRatio,
    CameraMotion,
    Generation,
    GenerationList,
    GenerateVideoRequest,
    VideoModel,
)

_BASE_URL = "https://api.higgsfield.ai"
_API_VERSION = "v1"


class HiggsFieldError(Exception):
    """Raised when the Higgsfield API returns an error."""
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Higgsfield API error {status_code}: {detail}")


class HiggsFieldClient:
    """Thin async wrapper around the Higgsfield AI REST API."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = _BASE_URL) -> None:
        self._api_key = api_key or os.environ.get("HIGGSFIELD_API_KEY", "")
        if not self._api_key:
            raise ValueError(
                "Higgsfield API key is required. Set HIGGSFIELD_API_KEY env var "
                "or pass api_key= to HiggsFieldClient()."
            )
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self._base_url}/{_API_VERSION}/{path.lstrip('/')}"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.request(
                method,
                self._url(path),
                headers=self._headers,
                json=json,
                params=params,
            )
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail") or resp.json().get("message") or resp.text
            except Exception:
                detail = resp.text
            raise HiggsFieldError(resp.status_code, detail)
        return resp.json()

    # ------------------------------------------------------------------
    # Video generation
    # ------------------------------------------------------------------

    async def generate_video(
        self,
        prompt: str,
        model: str = VideoModel.HIGGSFIELD_1,
        aspect_ratio: str = AspectRatio.LANDSCAPE,
        duration: int = 4,
        camera_motion: str = CameraMotion.STATIC,
        image_url: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> Generation:
        """Submit a new video generation job."""
        body: dict[str, Any] = {
            "prompt": prompt,
            "model": model,
            "aspect_ratio": aspect_ratio,
            "duration": duration,
            "camera_motion": camera_motion,
        }
        if image_url:
            body["image_url"] = image_url
        if negative_prompt:
            body["negative_prompt"] = negative_prompt
        if seed is not None:
            body["seed"] = seed

        data = await self._request("POST", "generate", json=body)
        return Generation(**data)

    async def get_generation(self, generation_id: str) -> Generation:
        """Fetch the current status of a generation."""
        data = await self._request("GET", f"generate/{generation_id}")
        return Generation(**data)

    async def list_generations(self, page: int = 1, limit: int = 10) -> GenerationList:
        """List past video generations (paginated)."""
        data = await self._request(
            "GET", "generate", params={"page": page, "limit": limit}
        )
        return GenerationList(**data)

    async def delete_generation(self, generation_id: str) -> dict[str, str]:
        """Delete a generation and its associated video file."""
        return await self._request("DELETE", f"generate/{generation_id}")

    # ------------------------------------------------------------------
    # Account / info
    # ------------------------------------------------------------------

    async def get_account(self) -> dict[str, Any]:
        """Return the current account info and usage quota."""
        return await self._request("GET", "account")
