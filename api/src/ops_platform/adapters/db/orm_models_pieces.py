"""ORM models for the Material/Piece traceability bounded context: the four
project-scoped catalogs (part numbers, conditions, locations, measurement
types) plus pieces, their condition tags, and their measurement values -
split out from orm_models.py to keep that module under the ~400-line limit
(CLAUDE.md §3). Shares the same `Base`/registry, so Alembic sees one
combined metadata."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ops_platform.adapters.db.orm_models import Base, enum_values
from ops_platform.domain.entities import PieceStatus


class PartNumberORM(Base):
    __tablename__ = "part_numbers"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_part_numbers_project_id_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class PieceConditionORM(Base):
    __tablename__ = "piece_conditions"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_piece_conditions_project_id_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class PieceLocationORM(Base):
    __tablename__ = "piece_locations"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_piece_locations_project_id_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class MeasurementTypeORM(Base):
    """`condition_id`/`part_number_id`/`status` independently scope which
    pieces this measurement applies to - all null means it applies to every
    piece (e.g. external diameter)."""

    __tablename__ = "measurement_types"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_measurement_types_project_id_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    condition_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("piece_conditions.id", ondelete="SET NULL"),
        nullable=True,
    )
    part_number_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("part_numbers.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[PieceStatus | None] = mapped_column(
        Enum(PieceStatus, name="piece_status", values_callable=enum_values, create_type=False),
        nullable=True,
    )


class PieceORM(Base):
    __tablename__ = "pieces"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tracking_number: Mapped[str] = mapped_column(String(6), unique=True, nullable=False)
    part_number_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("part_numbers.id"), nullable=False
    )
    overall_status: Mapped[PieceStatus] = mapped_column(
        Enum(PieceStatus, name="piece_status", values_callable=enum_values), nullable=False
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("piece_locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    conditions: Mapped[list[PieceConditionORM]] = relationship(
        secondary="piece_condition_links", lazy="selectin"
    )
    measurements: Mapped[list["PieceMeasurementORM"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan"
    )


class PieceConditionLinkORM(Base):
    """3NF join table: a piece can carry multiple condition tags, a condition
    applies to many pieces - same shape as `IssueLabelORM`."""

    __tablename__ = "piece_condition_links"

    piece_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("pieces.id", ondelete="CASCADE"), primary_key=True
    )
    condition_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("piece_conditions.id", ondelete="CASCADE"),
        primary_key=True,
    )


class PieceMeasurementORM(Base):
    __tablename__ = "piece_measurements"
    __table_args__ = (
        UniqueConstraint(
            "piece_id", "measurement_type_id", name="uq_piece_measurements_piece_type"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    piece_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("pieces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    measurement_type_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("measurement_types.id", ondelete="CASCADE"),
        nullable=False,
    )
    value: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)
