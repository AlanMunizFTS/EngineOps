"""remove plants/machines/implementations - project becomes a flat entity

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-19

Product decision: the `standard (project) > plant > machine > implementation`
hierarchy (ADR 0003) is removed. A project is now a single flat entity again -
no plants, no machines, no implementations, and no per-node phase override
(that mechanism only existed to let those nodes deviate from the project's
own Phase). The project-level Phase pipeline itself (ADR 0002,
`area_types`/`area_statuses`/`project_areas`) is untouched - it was never
part of the hierarchy, only inherited *by* it.

Issues (Phase 2) lose their `plant_id`/`machine_id`/`implementation_id`
hierarchy link and its CHECK constraint - an issue now only ever belongs to
`project_id` (see docs/architecture/adr/0005-remove-plant-hierarchy.md).

Pre-production schema: drops rather than migrates data, consistent with
0008/0009's precedent.

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_issues_single_hierarchy_link", "issues", type_="check")
    op.drop_column("issues", "plant_id")
    op.drop_column("issues", "machine_id")
    op.drop_column("issues", "implementation_id")

    op.drop_table("implementations")
    op.drop_table("machines")
    op.drop_table("plants")

    sa.Enum(name="implementation_status").drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
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
        sa.Column(
            "phase_status_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("area_statuses.id"),
            nullable=True,
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
        sa.Column(
            "phase_status_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("area_statuses.id"),
            nullable=True,
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
        sa.Column(
            "phase_status_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("area_statuses.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_implementations_machine_id", "implementations", ["machine_id"])

    op.add_column(
        "issues",
        sa.Column(
            "plant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("plants.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "issues",
        sa.Column(
            "machine_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("machines.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "issues",
        sa.Column(
            "implementation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("implementations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_issues_single_hierarchy_link",
        "issues",
        "(plant_id IS NOT NULL)::int + (machine_id IS NOT NULL)::int "
        "+ (implementation_id IS NOT NULL)::int <= 1",
    )
