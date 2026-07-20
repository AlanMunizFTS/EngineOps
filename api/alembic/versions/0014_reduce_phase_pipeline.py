"""reduce the Phase pipeline to Scope/Analysis/Stock/Development

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-19

Product decision: Designs, Approvals, Shipments, Implementation, and BuyOff
are dropped from the Phase pipeline (ADR 0002) - not needed for this
platform's scope. Buys is renamed to Stock. The remaining 4 phases move from
a sidebar stepper into the same top-level tab bar as Code/Issues/Kanban/
Milestones/Settings (frontend-only change, see
docs/architecture/adr/0005-project-simplification.md).

Same reseed pattern as 0009: pre-production, so old project_areas rows are
dropped and every project is backfilled to "Scope" rather than trying to
map old statuses (some of which no longer exist) onto the new 4.

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_PHASE_STATUSES: list[str] = ["Scope", "Analysis", "Stock", "Development"]
_OLD_PHASE_STATUSES: list[str] = [
    "Scope",
    "Analysis",
    "Designs",
    "Approvals",
    "Buys",
    "Shipments",
    "Development",
    "Implementation",
    "BuyOff",
]

_area_types_table = sa.table(
    "area_types",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("name", sa.String),
    sa.column("description", sa.String),
)
_area_statuses_table = sa.table(
    "area_statuses",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("area_type_id", postgresql.UUID(as_uuid=True)),
    sa.column("name", sa.String),
    sa.column("sort_order", sa.Integer),
)
_project_areas_table = sa.table(
    "project_areas",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("project_id", postgresql.UUID(as_uuid=True)),
    sa.column("area_type_id", postgresql.UUID(as_uuid=True)),
    sa.column("status_id", postgresql.UUID(as_uuid=True)),
)
_projects_table = sa.table("projects", sa.column("id", postgresql.UUID(as_uuid=True)))


def _reseed(conn: sa.Connection, statuses: list[str]) -> None:
    conn.execute(sa.text("DELETE FROM project_areas"))
    conn.execute(sa.text("DELETE FROM area_statuses"))
    conn.execute(sa.text("DELETE FROM area_types"))

    phase_type_id = uuid.uuid4()
    conn.execute(
        _area_types_table.insert().values(
            id=phase_type_id,
            name="Phase",
            description="Overall project phase - non-linear, moves freely between stages",
        )
    )

    status_ids = [uuid.uuid4() for _ in statuses]
    conn.execute(
        _area_statuses_table.insert(),
        [
            {"id": status_ids[i], "area_type_id": phase_type_id, "name": name, "sort_order": i}
            for i, name in enumerate(statuses)
        ],
    )

    scope_status_id = status_ids[0]
    project_ids = [row.id for row in conn.execute(sa.select(_projects_table.c.id))]
    if project_ids:
        conn.execute(
            _project_areas_table.insert(),
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


def upgrade() -> None:
    _reseed(op.get_bind(), _NEW_PHASE_STATUSES)


def downgrade() -> None:
    _reseed(op.get_bind(), _OLD_PHASE_STATUSES)
