from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from uuid import UUID

from ops_platform.domain.entities import (
    MeasurementType,
    PartNumber,
    Piece,
    PieceCondition,
    PieceLocation,
    PieceStatus,
)


class PieceRepository(ABC):
    """Port for the Material/Piece traceability bounded context - bundles the
    four project-scoped catalogs (part numbers, conditions, locations,
    measurement types) plus pieces themselves, mirroring how
    `KanbanRepository` bundles boards and columns."""

    @abstractmethod
    async def create_part_number(self, project_id: UUID, name: str) -> PartNumber: ...

    @abstractmethod
    async def list_part_numbers(self, project_id: UUID) -> list[PartNumber]: ...

    @abstractmethod
    async def create_piece_condition(self, project_id: UUID, name: str) -> PieceCondition: ...

    @abstractmethod
    async def list_piece_conditions(self, project_id: UUID) -> list[PieceCondition]: ...

    @abstractmethod
    async def create_piece_location(self, project_id: UUID, name: str) -> PieceLocation: ...

    @abstractmethod
    async def list_piece_locations(self, project_id: UUID) -> list[PieceLocation]: ...

    @abstractmethod
    async def create_measurement_type(
        self,
        project_id: UUID,
        name: str,
        unit: str,
        condition_id: UUID | None,
        part_number_id: UUID | None,
        status: PieceStatus | None,
    ) -> MeasurementType: ...

    @abstractmethod
    async def list_measurement_types(self, project_id: UUID) -> list[MeasurementType]: ...

    @abstractmethod
    async def get_measurement_type(self, measurement_type_id: UUID) -> MeasurementType | None: ...

    @abstractmethod
    async def update_measurement_type(
        self,
        measurement_type_id: UUID,
        *,
        name: str,
        unit: str,
        condition_id: UUID | None,
        part_number_id: UUID | None,
        status: PieceStatus | None,
    ) -> MeasurementType: ...

    @abstractmethod
    async def delete_measurement_type(self, measurement_type_id: UUID) -> None:
        """Cascades to any `piece_measurements` rows for this type."""
        ...

    @abstractmethod
    async def create_pieces(
        self,
        *,
        project_id: UUID,
        part_number_id: UUID,
        overall_status: PieceStatus,
        condition_ids: list[UUID],
        location_id: UUID | None,
        notes: str | None,
        created_by: UUID | None,
        quantity: int,
    ) -> list[Piece]:
        """Registers `quantity` pieces sharing every field, each stamped with
        its own unique `tracking_number` - the "group registration" path."""
        ...

    @abstractmethod
    async def get(self, piece_id: UUID) -> Piece | None: ...

    @abstractmethod
    async def list_for_project(
        self,
        project_id: UUID,
        *,
        part_number_id: UUID | None = None,
        status: PieceStatus | None = None,
        condition_ids: list[UUID] | None = None,
        location_id: UUID | None = None,
        measurement_type_id: UUID | None = None,
        measurement_min: Decimal | None = None,
        measurement_max: Decimal | None = None,
    ) -> list[Piece]: ...

    @abstractmethod
    async def update(
        self,
        piece_id: UUID,
        *,
        overall_status: PieceStatus,
        location_id: UUID | None,
        notes: str | None,
        condition_ids: list[UUID],
    ) -> Piece:
        """Replaces the piece's status/condition set and updates
        location/notes in one call - conditions are usually set once at
        registration, so a separate attach/detach surface would add
        ceremony without benefit."""
        ...

    @abstractmethod
    async def set_measurement(
        self, piece_id: UUID, measurement_type_id: UUID, value: Decimal
    ) -> Piece:
        """Upserts the value, respecting the one-row-per-type constraint."""
        ...
