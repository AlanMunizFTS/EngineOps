"""create material/piece traceability tables

Revision ID: 0025
Revises: 0024
Create Date: 2026-07-28

Adds the Material tab's data model: four project-scoped catalogs
(part_numbers, piece_conditions, piece_locations, measurement_types - each
mirroring `labels`' project_id+name uniqueness pattern), the `pieces` entity
itself, its `piece_condition_links` join table (same shape as
`issue_labels`), and `piece_measurements` (one value per measurement type
per piece, enforced by a unique constraint).

`piece_tracking_seq` backs each piece's unique tracking number - the
adapter reads `nextval()` and formats it as uppercase hex (e.g. "00001A")
in Python, not in SQL, keeping that logic visible/testable like the rest of
this codebase.

Purely additive: no existing table or column is touched.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE piece_tracking_seq")

    op.create_table(
        "part_numbers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.UniqueConstraint("project_id", "name", name="uq_part_numbers_project_id_name"),
    )
    op.create_index("ix_part_numbers_project_id", "part_numbers", ["project_id"])

    op.create_table(
        "piece_conditions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.UniqueConstraint("project_id", "name", name="uq_piece_conditions_project_id_name"),
    )
    op.create_index("ix_piece_conditions_project_id", "piece_conditions", ["project_id"])

    op.create_table(
        "piece_locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.UniqueConstraint("project_id", "name", name="uq_piece_locations_project_id_name"),
    )
    op.create_index("ix_piece_locations_project_id", "piece_locations", ["project_id"])

    op.create_table(
        "measurement_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column(
            "condition_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("piece_conditions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "part_number_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("part_numbers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint("project_id", "name", name="uq_measurement_types_project_id_name"),
    )
    op.create_index("ix_measurement_types_project_id", "measurement_types", ["project_id"])

    op.create_table(
        "pieces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tracking_number", sa.String(length=6), nullable=False, unique=True),
        sa.Column(
            "part_number_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("part_numbers.id"),
            nullable=False,
        ),
        sa.Column(
            "overall_status",
            postgresql.ENUM("ok", "nok", name="piece_status"),
            nullable=False,
        ),
        sa.Column(
            "location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("piece_locations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_pieces_project_id", "pieces", ["project_id"])

    op.create_table(
        "piece_condition_links",
        sa.Column(
            "piece_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pieces.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "condition_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("piece_conditions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_table(
        "piece_measurements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "piece_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pieces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "measurement_type_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("measurement_types.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("value", sa.Numeric(), nullable=False),
        sa.UniqueConstraint(
            "piece_id", "measurement_type_id", name="uq_piece_measurements_piece_type"
        ),
    )
    op.create_index("ix_piece_measurements_piece_id", "piece_measurements", ["piece_id"])


def downgrade() -> None:
    op.drop_table("piece_measurements")
    op.drop_table("piece_condition_links")
    op.drop_table("pieces")
    op.drop_table("measurement_types")
    op.drop_table("piece_locations")
    op.drop_table("piece_conditions")
    op.drop_table("part_numbers")

    sa.Enum(name="piece_status").drop(op.get_bind(), checkfirst=True)
    op.execute("DROP SEQUENCE piece_tracking_seq")
