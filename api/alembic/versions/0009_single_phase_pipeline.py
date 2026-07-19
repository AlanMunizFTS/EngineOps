"""collapse 6 domain areas into a single Phase pipeline (9 statuses)

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-19

See docs/architecture/adr/0002-single-phase-pipeline.md. Replaces the 6
domain-specific area_types (Scope & Charter, Procurement, Import/Export,
Electrical, Mechanical, Vision) with a single "Phase" area_type holding 9
statuses: Scope, Analysis, Designs, Approvals, Buys, Shipments, Development,
Implementation, BuyOff - non-linear/flexible, same project_areas mechanism as
before, just reseeded. Pre-production schema: existing project_areas rows are
dropped and every existing project is backfilled with a fresh "Scope" row
rather than carrying a data migration for the old per-domain statuses.

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PHASE_STATUSES: list[str] = [
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

# The original ADR 0001 seed, restored on downgrade (existing project_areas rows
# from this revision are not restorable - pre-production data only).
_LEGACY_AREA_TYPES: list[tuple[str, str]] = [
    ("Scope & Charter", "Defining project scope, charter, and stakeholder sign-off"),
    ("Procurement", "Sourcing, BOM definition, and purchasing"),
    ("Import/Export", "Cross-border logistics and customs documentation"),
    ("Electrical", "Electrical design and panel build"),
    ("Mechanical", "Mechanical design and fabrication"),
    ("Vision", "Vision system design and integration"),
]

_LEGACY_AREA_STATUSES: dict[str, list[str]] = {
    "Scope & Charter": [
        "Requested",
        "Analyzing",
        "Drafting Scope",
        "Awaiting Signature",
        "Approved",
    ],
    "Procurement": [
        "Not Started",
        "Defining BOM",
        "Awaiting Approval",
        "Ordered",
        "Awaiting Material",
        "Received",
    ],
    "Import/Export": ["Not Started", "Documentation", "Awaiting Customs", "Cleared", "Complete"],
    "Electrical": [
        "Not Started",
        "Designing",
        "Awaiting Approval",
        "Building",
        "Integrating",
        "Complete",
    ],
    "Mechanical": [
        "Not Started",
        "Designing",
        "Awaiting Approval",
        "Building",
        "Integrating",
        "Complete",
    ],
    "Vision": [
        "Not Started",
        "Designing",
        "Awaiting Approval",
        "Integrating",
        "Validating",
        "Complete",
    ],
}


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("DELETE FROM project_areas"))
    conn.execute(sa.text("DELETE FROM area_statuses"))
    conn.execute(sa.text("DELETE FROM area_types"))

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


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("DELETE FROM project_areas"))
    conn.execute(sa.text("DELETE FROM area_statuses"))
    conn.execute(sa.text("DELETE FROM area_types"))

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

    area_type_ids = {name: uuid.uuid4() for name, _ in _LEGACY_AREA_TYPES}
    conn.execute(
        area_types_table.insert(),
        [
            {"id": area_type_ids[name], "name": name, "description": description}
            for name, description in _LEGACY_AREA_TYPES
        ],
    )
    conn.execute(
        area_statuses_table.insert(),
        [
            {
                "id": uuid.uuid4(),
                "area_type_id": area_type_ids[area_name],
                "name": status_name,
                "sort_order": sort_order,
            }
            for area_name, statuses in _LEGACY_AREA_STATUSES.items()
            for sort_order, status_name in enumerate(statuses)
        ],
    )
