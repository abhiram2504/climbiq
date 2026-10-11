"""Add Phase 2 pose-processing metadata.

Revision ID: 20261011_0002
Revises: 20261010_0001
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261011_0002"
down_revision: str | None = "20261010_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("video_uploads", sa.Column("duration_ms", sa.Integer(), nullable=True))
    op.add_column("video_uploads", sa.Column("width", sa.Integer(), nullable=True))
    op.add_column("video_uploads", sa.Column("height", sa.Integer(), nullable=True))
    op.add_column("video_uploads", sa.Column("source_fps", sa.Float(), nullable=True))

    op.add_column(
        "processing_jobs",
        sa.Column("progress_current", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "processing_jobs",
        sa.Column("progress_total", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("processing_jobs", sa.Column("model_version", sa.String(100), nullable=True))
    op.add_column("processing_jobs", sa.Column("configuration_json", sa.JSON(), nullable=True))

    op.add_column(
        "pose_landmarks",
        sa.Column("detected", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.alter_column("pose_landmarks", "x", existing_type=sa.Float(), nullable=True)
    op.alter_column("pose_landmarks", "y", existing_type=sa.Float(), nullable=True)
    op.create_unique_constraint(
        "uq_pose_video_frame_landmark",
        "pose_landmarks",
        ["video_id", "frame_index", "landmark_name"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_pose_video_frame_landmark", "pose_landmarks", type_="unique"
    )
    op.execute("DELETE FROM pose_landmarks WHERE x IS NULL OR y IS NULL")
    op.alter_column("pose_landmarks", "y", existing_type=sa.Float(), nullable=False)
    op.alter_column("pose_landmarks", "x", existing_type=sa.Float(), nullable=False)
    op.drop_column("pose_landmarks", "detected")

    op.drop_column("processing_jobs", "configuration_json")
    op.drop_column("processing_jobs", "model_version")
    op.drop_column("processing_jobs", "progress_total")
    op.drop_column("processing_jobs", "progress_current")

    op.drop_column("video_uploads", "source_fps")
    op.drop_column("video_uploads", "height")
    op.drop_column("video_uploads", "width")
    op.drop_column("video_uploads", "duration_ms")
