"""create project_areas

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-18

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_areas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "area_type_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("area_types.id"),
            nullable=False,
        ),
        sa.Column(
            "status_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("area_statuses.id"),
            nullable=False,
        ),
        sa.Column(
            "updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_project_areas_project_id", "project_areas", ["project_id"])
    op.create_unique_constraint(
        "uq_project_areas_project_area_type", "project_areas", ["project_id", "area_type_id"]
    )


def downgrade() -> None:
    op.drop_table("project_areas")
