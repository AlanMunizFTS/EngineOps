"""remove the Phase pipeline entirely

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-20

Product decision: the project-level Phase pipeline (ADR 0001/0002, reduced to
Scope/Analysis/Stock/Development by 0014 and moved into the tab bar by ADR
0005) is dropped outright - not needed for this platform's scope. The
`project_areas`/`area_statuses`/`area_types` mechanism and its per-project
tab are removed with no replacement (see docs/architecture/adr/0006).

Pre-production schema: drops rather than migrates data, consistent with
0008/0009/0013's precedent.

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PHASE_STATUSES: list[str] = ["Scope", "Analysis", "Stock", "Development"]


def upgrade() -> None:
    op.drop_table("project_areas")
    op.drop_table("area_statuses")
    op.drop_table("area_types")


def downgrade() -> None:
    op.create_table(
        "area_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("description", sa.String(length=255), nullable=True),
    )
    op.create_table(
        "area_statuses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "area_type_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("area_types.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
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

    area_types_table = sa.table(
        "area_types",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
    )
    area_statuses_table = sa.table(
        "area_statuses",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("area_type_id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("sort_order", sa.Integer),
    )
    project_areas_table = sa.table(
        "project_areas",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("project_id", postgresql.UUID(as_uuid=True)),
        sa.column("area_type_id", postgresql.UUID(as_uuid=True)),
        sa.column("status_id", postgresql.UUID(as_uuid=True)),
    )
    projects_table = sa.table("projects", sa.column("id", postgresql.UUID(as_uuid=True)))

    conn = op.get_bind()
    phase_type_id = uuid.uuid4()
    conn.execute(
        area_types_table.insert().values(
            id=phase_type_id,
            name="Phase",
            description="Overall project phase - non-linear, moves freely between stages",
        )
    )

    status_ids = [uuid.uuid4() for _ in _PHASE_STATUSES]
    conn.execute(
        area_statuses_table.insert(),
        [
            {"id": status_ids[i], "area_type_id": phase_type_id, "name": name, "sort_order": i}
            for i, name in enumerate(_PHASE_STATUSES)
        ],
    )

    scope_status_id = status_ids[0]
    project_ids = [row.id for row in conn.execute(sa.select(projects_table.c.id))]
    if project_ids:
        conn.execute(
            project_areas_table.insert(),
            [
                {
                    "id": uuid.uuid4(),
                    "project_id": project_id,
                    "area_type_id": phase_type_id,
                    "status_id": scope_status_id,
                }
                for project_id in project_ids
            ],
        )
