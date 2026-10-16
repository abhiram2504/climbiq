from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import (
    ClimbDiscipline,
    ClimbOutcome,
    ClimbSource,
    ProcessingStatus,
    ProjectStatus,
)


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    database: Literal["connected", "unavailable"]


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    picture_url: str | None


class GmailConnectionResponse(BaseModel):
    connected: bool
    email: str | None = None
    scopes: list[str] = Field(default_factory=list)
    connected_at: datetime | None = None


class AuthStatusResponse(BaseModel):
    authenticated: bool
    google_oauth_configured: bool
    user: UserResponse | None = None
    gmail: GmailConnectionResponse


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    original_filename: str
    content_type: str
    size_bytes: int
    duration_ms: int | None
    width: int | None
    height: int | None
    source_fps: float | None
    status: ProcessingStatus
    error_message: str | None
    progress_percent: int | None = None
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
    progress_current: int
    progress_total: int
    progress_percent: int | None
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


class ClimbResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: ClimbSource
    discipline: ClimbDiscipline
    external_id: str | None
    name: str
    grade: str
    grade_system: str | None
    location: str | None
    route_type: str | None
    external_url: str | None
    pitches: int | None
    length_ft: int | None
    board_name: str | None
    board_angle: int | None
    setter: str | None
    is_benchmark: bool


class LogbookEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID | None
    climbed_on: date
    outcome: ClimbOutcome
    ascent_type: str | None
    attempts: int
    rating: float | None
    notes: str | None
    import_source: str | None
    created_at: datetime
    climb: ClimbResponse


class LogbookListResponse(BaseModel):
    items: list[LogbookEntryResponse]
    total: int


class CreateLogbookEntryRequest(BaseModel):
    project_id: UUID | None = None
    discipline: ClimbDiscipline
    source: ClimbSource = ClimbSource.manual
    external_id: str | None = Field(default=None, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    grade: str = Field(min_length=1, max_length=32)
    grade_system: str | None = Field(default=None, max_length=32)
    location: str | None = Field(default=None, max_length=500)
    route_type: str | None = Field(default=None, max_length=100)
    external_url: str | None = Field(default=None, max_length=1000)
    board_name: str | None = Field(default=None, max_length=100)
    board_angle: int | None = Field(default=None, ge=0, le=70)
    setter: str | None = Field(default=None, max_length=160)
    is_benchmark: bool = False
    climbed_on: date
    outcome: ClimbOutcome
    ascent_type: str | None = Field(default=None, max_length=32)
    attempts: int = Field(default=1, ge=1, le=999)
    rating: float | None = Field(default=None, ge=0, le=5)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("external_url")
    @classmethod
    def validate_external_url(cls, value: str | None) -> str | None:
        cleaned = (value or "").strip()
        if not cleaned:
            return None
        parsed = urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("External URL must use HTTP or HTTPS.")
        return cleaned


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    grade: str = Field(min_length=1, max_length=32)
    location: str | None = Field(default=None, max_length=500)
    route_type: str | None = Field(default=None, max_length=100)
    external_url: str | None = Field(default=None, max_length=1000)
    demand_tags: list[str] = Field(default_factory=list, max_length=8)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("external_url")
    @classmethod
    def validate_external_url(cls, value: str | None) -> str | None:
        cleaned = (value or "").strip()
        if not cleaned:
            return None
        parsed = urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("External URL must use HTTP or HTTPS.")
        return cleaned

    @field_validator("demand_tags")
    @classmethod
    def normalize_demand_tags(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            cleaned = value.strip().casefold()
            if not cleaned or cleaned in normalized:
                continue
            if len(cleaned) > 32:
                raise ValueError("Project demand tags must be 32 characters or fewer.")
            normalized.append(cleaned)
        return normalized


class CreateProjectDrillRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    grade: str = Field(min_length=1, max_length=32)
    focus: str | None = Field(default=None, max_length=160)


class UpdateProjectStatusRequest(BaseModel):
    status: ProjectStatus


class ProjectDrillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    focus: str | None
    created_at: datetime
    climb: ClimbResponse
    sent: bool = False


class ProjectResponse(BaseModel):
    id: UUID
    status: ProjectStatus
    demand_tags: list[str]
    notes: str | None
    created_at: datetime
    updated_at: datetime
    target_climb: ClimbResponse
    drills: list[ProjectDrillResponse]
    outdoor_attempts: int
    board_sessions: int
    drill_sends: int
    momentum_score: int
    next_action: str
    last_activity: date | None


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]


class ImportLogbookResponse(BaseModel):
    imported: int
    skipped: int
    errors: list[str] = Field(default_factory=list)


class ProgressPointResponse(BaseModel):
    period: str
    outdoor: int
    moonboard: int
    attempts: int


class LogbookSummaryResponse(BaseModel):
    total_entries: int
    total_sends: int
    outdoor_sends: int
    moonboard_sends: int
    days_climbed: int
    hardest_outdoor: str | None
    hardest_moonboard: str | None
    progress: list[ProgressPointResponse]
