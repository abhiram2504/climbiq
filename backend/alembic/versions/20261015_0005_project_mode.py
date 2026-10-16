"""Add outdoor project mode and MoonBoard training drills.

Revision ID: 20261015_0005
Revises: 20261014_0004
Create Date: 2026-10-15
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261015_0005"
down_revision: str | None = "20261014_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "climbing_projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("target_climb_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("demand_tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["target_climb_id"], ["climbs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_climbing_projects_user_id", "climbing_projects", ["user_id"])
    op.create_index(
        "ix_climbing_projects_target_climb_id",
        "climbing_projects",
        ["target_climb_id"],
    )
    op.create_index("ix_climbing_projects_status", "climbing_projects", ["status"])
    op.create_index("ix_projects_user_status", "climbing_projects", ["user_id", "status"])

    op.create_table(
        "project_drills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("climb_id", sa.Uuid(), nullable=False),
        sa.Column("focus", sa.String(length=160), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["climb_id"], ["climbs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["climbing_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "climb_id", name="uq_project_drill_climb"),
    )
    op.create_index("ix_project_drills_project_id", "project_drills", ["project_id"])
    op.create_index("ix_project_drills_climb_id", "project_drills", ["climb_id"])

    op.add_column("climb_log_entries", sa.Column("project_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_logbook_project",
        "climb_log_entries",
        "climbing_projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_climb_log_entries_project_id", "climb_log_entries", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_climb_log_entries_project_id", table_name="climb_log_entries")
    op.drop_constraint("fk_logbook_project", "climb_log_entries", type_="foreignkey")
    op.drop_column("climb_log_entries", "project_id")
    op.drop_index("ix_project_drills_climb_id", table_name="project_drills")
    op.drop_index("ix_project_drills_project_id", table_name="project_drills")
    op.drop_table("project_drills")
    op.drop_index("ix_projects_user_status", table_name="climbing_projects")
    op.drop_index("ix_climbing_projects_status", table_name="climbing_projects")
    op.drop_index("ix_climbing_projects_target_climb_id", table_name="climbing_projects")
    op.drop_index("ix_climbing_projects_user_id", table_name="climbing_projects")
    op.drop_table("climbing_projects")
