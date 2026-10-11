from __future__ import annotations

import enum
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ProcessingStatus(enum.StrEnum):
    uploaded = "uploaded"
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class ClimbingSession(Base):
    __tablename__ = "climbing_sessions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(160))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    videos: Mapped[list[VideoUpload]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


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
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[UUID] = mapped_column(ForeignKey("video_uploads.id", ondelete="CASCADE"))
    frame_index: Mapped[int] = mapped_column(Integer)
    timestamp_ms: Mapped[int] = mapped_column(Integer)
    landmark_name: Mapped[str] = mapped_column(String(50))
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
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
