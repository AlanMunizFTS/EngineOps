"""create plants, move machines under plants instead of projects

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-19

Introduces the missing level in the hierarchy: `standard (project) > plant >
machine > implementation` - a project's standard deployment rolls out to many
physical plants, each with its own machines. Pre-production schema, so this
migration drops and recreates `machines`/`implementations` rather than carrying
a data migration for the now-required `plant_id`.

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("implementations")
    op.drop_table("machines")

    op.create_table(
        "plants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_plants_project_id", "plants", ["project_id"])

    op.create_table(
        "machines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "plant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("plants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("machine_type", sa.String(length=100), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_machines_plant_id", "machines", ["plant_id"])

    op.create_table(
        "implementations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "machine_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("machines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "planned",
                "active",
                "superseded",
                "decommissioned",
                name="implementation_status",
                create_type=False,
            ),
            nullable=False,
            server_default="planned",
        ),
        sa.Column(
            "superseded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("implementations.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_implementations_machine_id", "implementations", ["machine_id"])


def downgrade() -> None:
    op.drop_table("implementations")
    op.drop_table("machines")
    op.drop_table("plants")

    op.create_table(
        "machines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("machine_type", sa.String(length=100), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_machines_project_id", "machines", ["project_id"])

    op.create_table(
        "implementations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "machine_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("machines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "planned",
                "active",
                "superseded",
                "decommissioned",
                name="implementation_status",
                create_type=False,
            ),
            nullable=False,
            server_default="planned",
        ),
        sa.Column(
            "superseded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("implementations.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_implementations_machine_id", "implementations", ["machine_id"])
