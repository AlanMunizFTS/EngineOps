"""create area_types, area_statuses (seeded catalog)

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-18

See docs/architecture/adr/0001 for why project progress is tracked as multiple
independent area tracks instead of a single projects.status field. This migration
seeds a starting vocabulary; new areas/statuses are a data insert, not a migration.

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_AREA_TYPES: list[tuple[str, str]] = [
    ("Scope & Charter", "Defining project scope, charter, and stakeholder sign-off"),
    ("Procurement", "Sourcing, BOM definition, and purchasing"),
    ("Import/Export", "Cross-border logistics and customs documentation"),
    ("Electrical", "Electrical design and panel build"),
    ("Mechanical", "Mechanical design and fabrication"),
    ("Vision", "Vision system design and integration"),
]

_AREA_STATUSES: dict[str, list[str]] = {
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

    area_type_ids: dict[str, uuid.UUID] = {name: uuid.uuid4() for name, _ in _AREA_TYPES}

    op.bulk_insert(
        area_types_table,
        [
            {"id": area_type_ids[name], "name": name, "description": description}
            for name, description in _AREA_TYPES
        ],
    )

    op.bulk_insert(
        area_statuses_table,
        [
            {
                "id": uuid.uuid4(),
                "area_type_id": area_type_ids[area_name],
                "name": status_name,
                "sort_order": sort_order,
            }
            for area_name, statuses in _AREA_STATUSES.items()
            for sort_order, status_name in enumerate(statuses)
        ],
    )


def downgrade() -> None:
    op.drop_table("area_statuses")
    op.drop_table("area_types")
