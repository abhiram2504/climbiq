"""Create Phase 1 schema.

Revision ID: 20261010_0001
Revises:
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261010_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

processing_status = sa.Enum(
    "uploaded",
    "queued",
    "processing",
    "completed",
    "failed",
    name="processingstatus",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "climbing_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_climbing_sessions_created_at", "climbing_sessions", ["created_at"])

    op.create_table(
        "video_uploads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("annotated_storage_key", sa.String(length=500), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("status", processing_status, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["climbing_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("annotated_storage_key"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_video_uploads_created_at", "video_uploads", ["created_at"])
    op.create_index("ix_video_uploads_session_id", "video_uploads", ["session_id"])
    op.create_index("ix_video_uploads_status", "video_uploads", ["status"])

    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("status", processing_status, nullable=False),
        sa.Column("task_name", sa.String(length=100), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["video_id"], ["video_uploads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_processing_jobs_video_id", "processing_jobs", ["video_id"])

    op.create_table(
        "pose_landmarks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("frame_index", sa.Integer(), nullable=False),
        sa.Column("timestamp_ms", sa.Integer(), nullable=False),
        sa.Column("landmark_name", sa.String(length=50), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("z", sa.Float(), nullable=True),
        sa.Column("visibility", sa.Float(), nullable=True),
        sa.Column("presence", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["video_id"], ["video_uploads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pose_video_frame", "pose_landmarks", ["video_id", "frame_index"])
    op.create_index("ix_pose_video_timestamp", "pose_landmarks", ["video_id", "timestamp_ms"])

    op.create_table(
        "movement_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("timestamp_ms", sa.Integer(), nullable=False),
        sa.Column("metric_name", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["video_id"], ["video_uploads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_metric_video_time", "movement_metrics", ["video_id", "timestamp_ms"])
    op.create_index("ix_movement_metrics_metric_name", "movement_metrics", ["metric_name"])

    op.create_table(
        "technique_observations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("video_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("start_timestamp_ms", sa.Integer(), nullable=False),
        sa.Column("end_timestamp_ms", sa.Integer(), nullable=True),
        sa.Column("observation_text", sa.Text(), nullable=False),
        sa.Column("recommendation_text", sa.Text(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["video_id"], ["video_uploads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_technique_observations_video_id", "technique_observations", ["video_id"])


def downgrade() -> None:
    op.drop_index("ix_technique_observations_video_id", table_name="technique_observations")
    op.drop_table("technique_observations")
    op.drop_index("ix_movement_metrics_metric_name", table_name="movement_metrics")
    op.drop_index("ix_metric_video_time", table_name="movement_metrics")
    op.drop_table("movement_metrics")
    op.drop_index("ix_pose_video_timestamp", table_name="pose_landmarks")
    op.drop_index("ix_pose_video_frame", table_name="pose_landmarks")
    op.drop_table("pose_landmarks")
    op.drop_index("ix_processing_jobs_video_id", table_name="processing_jobs")
    op.drop_table("processing_jobs")
    op.drop_index("ix_video_uploads_status", table_name="video_uploads")
    op.drop_index("ix_video_uploads_session_id", table_name="video_uploads")
    op.drop_index("ix_video_uploads_created_at", table_name="video_uploads")
    op.drop_table("video_uploads")
    op.drop_index("ix_climbing_sessions_created_at", table_name="climbing_sessions")
    op.drop_table("climbing_sessions")
