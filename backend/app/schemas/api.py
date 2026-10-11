from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models import ProcessingStatus


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    database: Literal["connected", "unavailable"]


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    original_filename: str
    content_type: str
    size_bytes: int
    status: ProcessingStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    stream_url: str = ""
    status_url: str = ""
    analysis_url: str = ""
    annotated_url: str | None = None


class VideoListResponse(BaseModel):
    items: list[VideoResponse]
    total: int


class VideoStatusResponse(BaseModel):
    video_id: UUID
    status: ProcessingStatus
    error_message: str | None
    updated_at: datetime


class MovementMetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp_ms: int
    metric_name: str
    value: float
    unit: str
    confidence: float | None
    metadata_json: dict[str, Any] | None


class TechniqueObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    start_timestamp_ms: int
    end_timestamp_ms: int | None
    observation_text: str
    recommendation_text: str | None
    evidence: dict[str, Any]


class AnalysisResponse(BaseModel):
    video_id: UUID
    analysis_status: Literal["not_started", "processing", "completed", "failed"]
    disclaimer: str
    metrics: list[MovementMetricResponse]
    observations: list[TechniqueObservationResponse]


class SessionResponse(BaseModel):
    id: UUID
    title: str
    notes: str | None
    created_at: datetime
    attempt_count: int


class SessionListResponse(BaseModel):
    items: list[SessionResponse]
    total: int
