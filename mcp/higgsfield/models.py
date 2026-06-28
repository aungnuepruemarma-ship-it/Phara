"""Pydantic models for the Higgsfield AI API."""
from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, HttpUrl


class AspectRatio(str, Enum):
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    SQUARE = "1:1"


class CameraMotion(str, Enum):
    STATIC = "static"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    TILT_UP = "tilt_up"
    TILT_DOWN = "tilt_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    ORBIT_LEFT = "orbit_left"
    ORBIT_RIGHT = "orbit_right"
    CRANE_UP = "crane_up"
    CRANE_DOWN = "crane_down"
    DOLLY_IN = "dolly_in"
    DOLLY_OUT = "dolly_out"


class VideoModel(str, Enum):
    HIGGSFIELD_1 = "higgsfield-1"
    DIFFUSION_1 = "diffusion-1"


class GenerationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerateVideoRequest(BaseModel):
    prompt: str
    model: VideoModel = VideoModel.HIGGSFIELD_1
    aspect_ratio: AspectRatio = AspectRatio.LANDSCAPE
    duration: int = 4  # seconds: 4 | 6 | 8
    camera_motion: CameraMotion = CameraMotion.STATIC
    image_url: Optional[str] = None  # for image-to-video
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None


class Generation(BaseModel):
    id: str
    status: GenerationStatus
    prompt: Optional[str] = None
    model: Optional[str] = None
    aspect_ratio: Optional[str] = None
    duration: Optional[int] = None
    camera_motion: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class GenerationList(BaseModel):
    items: list[Generation]
    total: int
    page: int
    limit: int
