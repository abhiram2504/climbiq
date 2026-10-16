"""Add the unified outdoor and board-climbing logbook.

Revision ID: 20261014_0004
Revises: 20261011_0003
Create Date: 2026-10-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261014_0004"
down_revision: str | None = "20261011_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "climbs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("identity_key", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("discipline", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("grade", sa.String(length=32), nullable=False),
        sa.Column("grade_system", sa.String(length=32), nullable=True),
        sa.Column("location", sa.String(length=500), nullable=True),
        sa.Column("route_type", sa.String(length=100), nullable=True),
        sa.Column("external_url", sa.String(length=1000), nullable=True),
        sa.Column("pitches", sa.Integer(), nullable=True),
        sa.Column("length_ft", sa.Integer(), nullable=True),
        sa.Column("board_name", sa.String(length=100), nullable=True),
        sa.Column("board_angle", sa.Integer(), nullable=True),
        sa.Column("setter", sa.String(length=160), nullable=True),
        sa.Column("is_benchmark", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "identity_key", name="uq_climbs_user_identity"),
    )
    op.create_index("ix_climbs_name", "climbs", ["name"])
    op.create_index("ix_climbs_source", "climbs", ["source"])
    op.create_index("ix_climbs_discipline", "climbs", ["discipline"])
    op.create_index("ix_climbs_user_id", "climbs", ["user_id"])
    op.create_index("ix_climbs_user_discipline", "climbs", ["user_id", "discipline"])

    op.create_table(
        "climb_log_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("climb_id", sa.Uuid(), nullable=False),
        sa.Column("climbed_on", sa.Date(), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("ascent_type", sa.String(length=32), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("import_source", sa.String(length=64), nullable=True),
        sa.Column("source_entry_key", sa.String(length=64), nullable=True),
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
        sa.ForeignKeyConstraint(["climb_id"], ["climbs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "source_entry_key", name="uq_logbook_user_source_entry"),
    )
    op.create_index("ix_climb_log_entries_user_id", "climb_log_entries", ["user_id"])
    op.create_index("ix_climb_log_entries_climb_id", "climb_log_entries", ["climb_id"])
    op.create_index("ix_climb_log_entries_climbed_on", "climb_log_entries", ["climbed_on"])
    op.create_index("ix_climb_log_entries_outcome", "climb_log_entries", ["outcome"])
    op.create_index("ix_logbook_user_date", "climb_log_entries", ["user_id", "climbed_on"])


def downgrade() -> None:
    op.drop_index("ix_logbook_user_date", table_name="climb_log_entries")
    op.drop_index("ix_climb_log_entries_outcome", table_name="climb_log_entries")
    op.drop_index("ix_climb_log_entries_climbed_on", table_name="climb_log_entries")
    op.drop_index("ix_climb_log_entries_climb_id", table_name="climb_log_entries")
    op.drop_index("ix_climb_log_entries_user_id", table_name="climb_log_entries")
    op.drop_table("climb_log_entries")
    op.drop_index("ix_climbs_user_discipline", table_name="climbs")
    op.drop_index("ix_climbs_user_id", table_name="climbs")
    op.drop_index("ix_climbs_discipline", table_name="climbs")
    op.drop_index("ix_climbs_source", table_name="climbs")
    op.drop_index("ix_climbs_name", table_name="climbs")
    op.drop_table("climbs")
