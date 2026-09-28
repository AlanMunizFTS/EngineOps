"""remove milestones

Revision ID: 0024
Revises: 0023
Create Date: 2026-07-28

The Milestones feature (tab, API, and its `milestones` table) is removed
outright - not deprecated - per an explicit product decision to drop it
project-wide. Drops `issues.milestone_id` first (it FKs into `milestones`),
then the `milestones` table and its `milestone_status` enum type.

Downgrade recreates the schema (table + FK + enum) but cannot restore any
milestone rows or `milestone_id` links deleted by the upgrade - those are
gone once this runs.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("issues", "milestone_id")
    op.drop_index("ix_milestones_project_id", table_name="milestones")
    op.drop_table("milestones")
    sa.Enum(name="milestone_status").drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    op.create_table(
        "milestones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM("open", "closed", name="milestone_status"),
            nullable=False,
            server_default="open",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_milestones_project_id", "milestones", ["project_id"])
    op.add_column(
        "issues",
        sa.Column(
            "milestone_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("milestones.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
