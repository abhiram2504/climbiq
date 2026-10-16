from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ProcessingStatus(enum.StrEnum):
    uploaded = "uploaded"
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class ClimbSource(enum.StrEnum):
    manual = "manual"
    mountain_project = "mountain_project"
    moonboard = "moonboard"


class ClimbDiscipline(enum.StrEnum):
    outdoor = "outdoor"
    moonboard = "moonboard"


class ClimbOutcome(enum.StrEnum):
    attempt = "attempt"
    send = "send"


class ProjectStatus(enum.StrEnum):
    active = "active"
    sent = "sent"
    archived = "archived"


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    google_subject: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(160))
    picture_url: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    auth_sessions: Mapped[list[AuthSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    gmail_connection: Mapped[GmailConnection | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    climbing_sessions: Mapped[list[ClimbingSession]] = relationship(back_populates="user")
    climbs: Mapped[list[Climb]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    logbook_entries: Mapped[list[ClimbLogEntry]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    climbing_projects: Mapped[list[ClimbingProject]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="auth_sessions")


class OAuthFlow(Base):
    __tablename__ = "oauth_flows"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    purpose: Mapped[str] = mapped_column(String(32))
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    code_verifier: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GmailConnection(Base):
    __tablename__ = "gmail_connections"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    google_subject: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(320))
    access_token_encrypted: Mapped[str] = mapped_column(Text)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text)
    granted_scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="gmail_connection")


class ClimbingSession(Base):
    __tablename__ = "climbing_sessions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(160))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    videos: Mapped[list[VideoUpload]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    user: Mapped[User | None] = relationship(back_populates="climbing_sessions")


class Climb(Base):
    __tablename__ = "climbs"
    __table_args__ = (
        UniqueConstraint("user_id", "identity_key", name="uq_climbs_user_identity"),
        Index("ix_climbs_user_discipline", "user_id", "discipline"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    identity_key: Mapped[str] = mapped_column(String(64))
    source: Mapped[ClimbSource] = mapped_column(
        Enum(ClimbSource, native_enum=False, length=32), index=True
    )
    discipline: Mapped[ClimbDiscipline] = mapped_column(
        Enum(ClimbDiscipline, native_enum=False, length=32), index=True
    )
    external_id: Mapped[str | None] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255), index=True)
    grade: Mapped[str] = mapped_column(String(32))
    grade_system: Mapped[str | None] = mapped_column(String(32))
    location: Mapped[str | None] = mapped_column(String(500))
    route_type: Mapped[str | None] = mapped_column(String(100))
    external_url: Mapped[str | None] = mapped_column(String(1000))
    pitches: Mapped[int | None] = mapped_column(Integer)
    length_ft: Mapped[int | None] = mapped_column(Integer)
    board_name: Mapped[str | None] = mapped_column(String(100))
    board_angle: Mapped[int | None] = mapped_column(Integer)
    setter: Mapped[str | None] = mapped_column(String(160))
    is_benchmark: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="climbs")
    logbook_entries: Mapped[list[ClimbLogEntry]] = relationship(
        back_populates="climb", cascade="all, delete-orphan"
    )
    target_projects: Mapped[list[ClimbingProject]] = relationship(back_populates="target_climb")
    project_drills: Mapped[list[ProjectDrill]] = relationship(back_populates="climb")


class ClimbingProject(Base):
    __tablename__ = "climbing_projects"
    __table_args__ = (Index("ix_projects_user_status", "user_id", "status"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    target_climb_id: Mapped[UUID] = mapped_column(
        ForeignKey("climbs.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, native_enum=False, length=16),
        default=ProjectStatus.active,
        index=True,
    )
    demand_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="climbing_projects")
    target_climb: Mapped[Climb] = relationship(back_populates="target_projects")
    drills: Mapped[list[ProjectDrill]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    logbook_entries: Mapped[list[ClimbLogEntry]] = relationship(back_populates="project")


class ProjectDrill(Base):
    __tablename__ = "project_drills"
    __table_args__ = (
        UniqueConstraint("project_id", "climb_id", name="uq_project_drill_climb"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("climbing_projects.id", ondelete="CASCADE"), index=True
    )
    climb_id: Mapped[UUID] = mapped_column(
        ForeignKey("climbs.id", ondelete="RESTRICT"), index=True
    )
    focus: Mapped[str | None] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped[ClimbingProject] = relationship(back_populates="drills")
    climb: Mapped[Climb] = relationship(back_populates="project_drills")


class ClimbLogEntry(Base):
    __tablename__ = "climb_log_entries"
    __table_args__ = (
        UniqueConstraint("user_id", "source_entry_key", name="uq_logbook_user_source_entry"),
        Index("ix_logbook_user_date", "user_id", "climbed_on"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    climb_id: Mapped[UUID] = mapped_column(
        ForeignKey("climbs.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("climbing_projects.id", ondelete="SET NULL"), index=True
    )
    climbed_on: Mapped[date] = mapped_column(Date, index=True)
    outcome: Mapped[ClimbOutcome] = mapped_column(
        Enum(ClimbOutcome, native_enum=False, length=16), index=True
    )
    ascent_type: Mapped[str | None] = mapped_column(String(32))
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    rating: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    import_source: Mapped[str | None] = mapped_column(String(64))
    source_entry_key: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="logbook_entries")
    climb: Mapped[Climb] = relationship(back_populates="logbook_entries")
    project: Mapped[ClimbingProject | None] = relationship(back_populates="logbook_entries")


class VideoUpload(Base):
    __tablename__ = "video_uploads"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("climbing_sessions.id", ondelete="CASCADE"), index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    annotated_storage_key: Mapped[str | None] = mapped_column(String(500), unique=True)
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    source_fps: Mapped[float | None] = mapped_column(Float)
    status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, native_enum=False, length=32),
        default=ProcessingStatus.uploaded,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    session: Mapped[ClimbingSession] = relationship(back_populates="videos")
    jobs: Mapped[list[ProcessingJob]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    landmarks: Mapped[list[PoseLandmark]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    metrics: Mapped[list[MovementMetric]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    observations: Mapped[list[TechniqueObservation]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    video_id: Mapped[UUID] = mapped_column(
        ForeignKey("video_uploads.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, native_enum=False, length=32), default=ProcessingStatus.queued
    )
    task_name: Mapped[str] = mapped_column(String(100), default="pose_analysis")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    progress_current: Mapped[int] = mapped_column(Integer, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, default=0)
    model_version: Mapped[str | None] = mapped_column(String(100))
    configuration_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    video: Mapped[VideoUpload] = relationship(back_populates="jobs")


class PoseLandmark(Base):
    __tablename__ = "pose_landmarks"
    __table_args__ = (
        Index("ix_pose_video_frame", "video_id", "frame_index"),
        Index("ix_pose_video_timestamp", "video_id", "timestamp_ms"),
        UniqueConstraint(
            "video_id", "frame_index", "landmark_name", name="uq_pose_video_frame_landmark"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[UUID] = mapped_column(ForeignKey("video_uploads.id", ondelete="CASCADE"))
    frame_index: Mapped[int] = mapped_column(Integer)
    timestamp_ms: Mapped[int] = mapped_column(Integer)
    landmark_name: Mapped[str] = mapped_column(String(50))
    detected: Mapped[bool] = mapped_column(Boolean, default=True)
    x: Mapped[float | None] = mapped_column(Float)
    y: Mapped[float | None] = mapped_column(Float)
    z: Mapped[float | None] = mapped_column(Float)
    visibility: Mapped[float | None] = mapped_column(Float)
    presence: Mapped[float | None] = mapped_column(Float)

    video: Mapped[VideoUpload] = relationship(back_populates="landmarks")


class MovementMetric(Base):
    __tablename__ = "movement_metrics"
    __table_args__ = (Index("ix_metric_video_time", "video_id", "timestamp_ms"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[UUID] = mapped_column(ForeignKey("video_uploads.id", ondelete="CASCADE"))
    timestamp_ms: Mapped[int] = mapped_column(Integer)
    metric_name: Mapped[str] = mapped_column(String(100), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(30))
    confidence: Mapped[float | None] = mapped_column(Float)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    video: Mapped[VideoUpload] = relationship(back_populates="metrics")


class TechniqueObservation(Base):
    __tablename__ = "technique_observations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[UUID] = mapped_column(
        ForeignKey("video_uploads.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(100))
    start_timestamp_ms: Mapped[int] = mapped_column(Integer)
    end_timestamp_ms: Mapped[int | None] = mapped_column(Integer)
    observation_text: Mapped[str] = mapped_column(Text)
    recommendation_text: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    video: Mapped[VideoUpload] = relationship(back_populates="observations")
