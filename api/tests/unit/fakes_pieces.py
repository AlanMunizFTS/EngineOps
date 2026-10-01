"""In-memory fake for the Material/Piece traceability repository port - mirrors
the SQL adapter's filtering/upsert semantics without a real Postgres
connection (see fakes_tasks.py for the same pattern on the task-tracking
context)."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from ops_platform.domain.entities import (
    MeasurementType,
    PartNumber,
    Piece,
    PieceCondition,
    PieceLocation,
    PieceMeasurement,
    PieceStatus,
)
from ops_platform.domain.ports.piece_repository import PieceRepository


class FakePieceRepository(PieceRepository):
    def __init__(self) -> None:
        self._part_numbers: dict[UUID, PartNumber] = {}
        self._conditions: dict[UUID, PieceCondition] = {}
        self._locations: dict[UUID, PieceLocation] = {}
        self._measurement_types: dict[UUID, MeasurementType] = {}
        self._pieces: dict[UUID, Piece] = {}
        self._next_tracking_number = 1

    async def create_part_number(self, project_id: UUID, name: str) -> PartNumber:
        part_number = PartNumber(id=uuid.uuid4(), project_id=project_id, name=name)
        self._part_numbers[part_number.id] = part_number
        return part_number

    async def list_part_numbers(self, project_id: UUID) -> list[PartNumber]:
        return [p for p in self._part_numbers.values() if p.project_id == project_id]

    async def create_piece_condition(self, project_id: UUID, name: str) -> PieceCondition:
        condition = PieceCondition(id=uuid.uuid4(), project_id=project_id, name=name)
        self._conditions[condition.id] = condition
        return condition

    async def list_piece_conditions(self, project_id: UUID) -> list[PieceCondition]:
        return [c for c in self._conditions.values() if c.project_id == project_id]

    async def create_piece_location(self, project_id: UUID, name: str) -> PieceLocation:
        location = PieceLocation(id=uuid.uuid4(), project_id=project_id, name=name)
        self._locations[location.id] = location
        return location

    async def list_piece_locations(self, project_id: UUID) -> list[PieceLocation]:
        return [loc for loc in self._locations.values() if loc.project_id == project_id]

    async def create_measurement_type(
        self,
        project_id: UUID,
        name: str,
        unit: str,
        condition_id: UUID | None,
        part_number_id: UUID | None,
        status: PieceStatus | None,
    ) -> MeasurementType:
        measurement_type = MeasurementType(
            id=uuid.uuid4(),
            project_id=project_id,
            name=name,
            unit=unit,
            condition_id=condition_id,
            part_number_id=part_number_id,
            status=status,
        )
        self._measurement_types[measurement_type.id] = measurement_type
        return measurement_type

    async def list_measurement_types(self, project_id: UUID) -> list[MeasurementType]:
        return [t for t in self._measurement_types.values() if t.project_id == project_id]

    async def get_measurement_type(self, measurement_type_id: UUID) -> MeasurementType | None:
        return self._measurement_types.get(measurement_type_id)

    async def update_measurement_type(
        self,
        measurement_type_id: UUID,
        *,
        name: str,
        unit: str,
        condition_id: UUID | None,
        part_number_id: UUID | None,
        status: PieceStatus | None,
    ) -> MeasurementType:
        updated = replace(
            self._measurement_types[measurement_type_id],
            name=name,
            unit=unit,
            condition_id=condition_id,
            part_number_id=part_number_id,
            status=status,
        )
        self._measurement_types[measurement_type_id] = updated
        return updated

    async def delete_measurement_type(self, measurement_type_id: UUID) -> None:
        self._measurement_types.pop(measurement_type_id, None)
        for piece_id, piece in list(self._pieces.items()):
            remaining = [
                m for m in piece.measurements if m.measurement_type_id != measurement_type_id
            ]
            if len(remaining) != len(piece.measurements):
                self._pieces[piece_id] = replace(piece, measurements=remaining)

    def _next_hex_tracking_number(self) -> str:
        formatted = format(self._next_tracking_number, "06X")
        self._next_tracking_number += 1
        return formatted

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
        conditions = [self._conditions[cid] for cid in condition_ids]
        created = []
        for _ in range(quantity):
            piece = Piece(
                id=uuid.uuid4(),
                project_id=project_id,
                tracking_number=self._next_hex_tracking_number(),
                part_number_id=part_number_id,
                overall_status=overall_status,
                location_id=location_id,
                notes=notes,
                created_by=created_by,
                created_at=datetime.now(UTC),
                conditions=conditions,
            )
            self._pieces[piece.id] = piece
            created.append(piece)
        return created

    async def get(self, piece_id: UUID) -> Piece | None:
        return self._pieces.get(piece_id)

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
    ) -> list[Piece]:
        results = [p for p in self._pieces.values() if p.project_id == project_id]
        if part_number_id is not None:
            results = [p for p in results if p.part_number_id == part_number_id]
        if status is not None:
            results = [p for p in results if p.overall_status == status]
        if location_id is not None:
            results = [p for p in results if p.location_id == location_id]
        if condition_ids:
            wanted = set(condition_ids)
            results = [p for p in results if wanted <= {c.id for c in p.conditions}]
        if measurement_type_id is not None:
            filtered = []
            for piece in results:
                value = next(
                    (
                        m.value
                        for m in piece.measurements
                        if m.measurement_type_id == measurement_type_id
                    ),
                    None,
                )
                if value is None:
                    continue
                if measurement_min is not None and value < measurement_min:
                    continue
                if measurement_max is not None and value > measurement_max:
                    continue
                filtered.append(piece)
            results = filtered
        return sorted(results, key=lambda p: p.tracking_number)

    async def update(
        self,
        piece_id: UUID,
        *,
        overall_status: PieceStatus,
        location_id: UUID | None,
        notes: str | None,
        condition_ids: list[UUID],
    ) -> Piece:
        conditions = [self._conditions[cid] for cid in condition_ids]
        updated = replace(
            self._pieces[piece_id],
            overall_status=overall_status,
            location_id=location_id,
            notes=notes,
            conditions=conditions,
        )
        self._pieces[piece_id] = updated
        return updated

    async def set_measurement(
        self, piece_id: UUID, measurement_type_id: UUID, value: Decimal
    ) -> Piece:
        piece = self._pieces[piece_id]
        existing = [m for m in piece.measurements if m.measurement_type_id != measurement_type_id]
        new_measurement = PieceMeasurement(
            id=uuid.uuid4(),
            piece_id=piece_id,
            measurement_type_id=measurement_type_id,
            value=value,
        )
        updated = replace(piece, measurements=[*existing, new_measurement])
        self._pieces[piece_id] = updated
        return updated
