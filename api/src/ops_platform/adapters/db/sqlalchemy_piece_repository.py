from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models_pieces import (
    MeasurementTypeORM,
    PartNumberORM,
    PieceConditionLinkORM,
    PieceConditionORM,
    PieceLocationORM,
    PieceMeasurementORM,
    PieceORM,
)
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


def _to_part_number(orm: PartNumberORM) -> PartNumber:
    return PartNumber(id=orm.id, project_id=orm.project_id, name=orm.name)


def _to_condition(orm: PieceConditionORM) -> PieceCondition:
    return PieceCondition(id=orm.id, project_id=orm.project_id, name=orm.name)


def _to_location(orm: PieceLocationORM) -> PieceLocation:
    return PieceLocation(id=orm.id, project_id=orm.project_id, name=orm.name)


def _to_measurement_type(orm: MeasurementTypeORM) -> MeasurementType:
    return MeasurementType(
        id=orm.id,
        project_id=orm.project_id,
        name=orm.name,
        unit=orm.unit,
        condition_id=orm.condition_id,
        part_number_id=orm.part_number_id,
        status=orm.status,
    )


def _to_measurement(orm: PieceMeasurementORM) -> PieceMeasurement:
    return PieceMeasurement(
        id=orm.id,
        piece_id=orm.piece_id,
        measurement_type_id=orm.measurement_type_id,
        value=orm.value,
    )


def _to_piece(orm: PieceORM) -> Piece:
    return Piece(
        id=orm.id,
        project_id=orm.project_id,
        tracking_number=orm.tracking_number,
        part_number_id=orm.part_number_id,
        overall_status=orm.overall_status,
        location_id=orm.location_id,
        notes=orm.notes,
        created_by=orm.created_by,
        created_at=orm.created_at,
        conditions=[_to_condition(c) for c in orm.conditions],
        measurements=[_to_measurement(m) for m in orm.measurements],
    )


class SqlAlchemyPieceRepository(PieceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_part_number(self, project_id: UUID, name: str) -> PartNumber:
        orm = PartNumberORM(project_id=project_id, name=name)
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _to_part_number(orm)

    async def list_part_numbers(self, project_id: UUID) -> list[PartNumber]:
        result = await self._session.execute(
            select(PartNumberORM)
            .where(PartNumberORM.project_id == project_id)
            .order_by(PartNumberORM.name)
        )
        return [_to_part_number(row) for row in result.scalars().all()]

    async def create_piece_condition(self, project_id: UUID, name: str) -> PieceCondition:
        orm = PieceConditionORM(project_id=project_id, name=name)
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _to_condition(orm)

    async def list_piece_conditions(self, project_id: UUID) -> list[PieceCondition]:
        result = await self._session.execute(
            select(PieceConditionORM)
            .where(PieceConditionORM.project_id == project_id)
            .order_by(PieceConditionORM.name)
        )
        return [_to_condition(row) for row in result.scalars().all()]

    async def create_piece_location(self, project_id: UUID, name: str) -> PieceLocation:
        orm = PieceLocationORM(project_id=project_id, name=name)
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _to_location(orm)

    async def list_piece_locations(self, project_id: UUID) -> list[PieceLocation]:
        result = await self._session.execute(
            select(PieceLocationORM)
            .where(PieceLocationORM.project_id == project_id)
            .order_by(PieceLocationORM.name)
        )
        return [_to_location(row) for row in result.scalars().all()]

    async def create_measurement_type(
        self,
        project_id: UUID,
        name: str,
        unit: str,
        condition_id: UUID | None,
        part_number_id: UUID | None,
        status: PieceStatus | None,
    ) -> MeasurementType:
        orm = MeasurementTypeORM(
            project_id=project_id,
            name=name,
            unit=unit,
            condition_id=condition_id,
            part_number_id=part_number_id,
            status=status,
        )
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm)
        return _to_measurement_type(orm)

    async def list_measurement_types(self, project_id: UUID) -> list[MeasurementType]:
        result = await self._session.execute(
            select(MeasurementTypeORM)
            .where(MeasurementTypeORM.project_id == project_id)
            .order_by(MeasurementTypeORM.name)
        )
        return [_to_measurement_type(row) for row in result.scalars().all()]

    async def get_measurement_type(self, measurement_type_id: UUID) -> MeasurementType | None:
        orm = await self._session.get(MeasurementTypeORM, measurement_type_id)
        return _to_measurement_type(orm) if orm else None

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
        orm = await self._session.get(MeasurementTypeORM, measurement_type_id)
        if orm is None:
            raise ValueError(f"measurement type {measurement_type_id} not found")
        orm.name = name
        orm.unit = unit
        orm.condition_id = condition_id
        orm.part_number_id = part_number_id
        orm.status = status
        await self._session.flush()
        await self._session.refresh(orm)
        return _to_measurement_type(orm)

    async def delete_measurement_type(self, measurement_type_id: UUID) -> None:
        orm = await self._session.get(MeasurementTypeORM, measurement_type_id)
        if orm is None:
            raise ValueError(f"measurement type {measurement_type_id} not found")
        await self._session.delete(orm)
        await self._session.flush()

    async def _next_tracking_number(self) -> str:
        result = await self._session.execute(select(func.nextval("piece_tracking_seq")))
        return format(result.scalar_one(), "06X")

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
        created: list[PieceORM] = []
        for _ in range(quantity):
            orm_piece = PieceORM(
                project_id=project_id,
                tracking_number=await self._next_tracking_number(),
                part_number_id=part_number_id,
                overall_status=overall_status,
                location_id=location_id,
                notes=notes,
                created_by=created_by,
            )
            self._session.add(orm_piece)
            await self._session.flush()
            for condition_id in condition_ids:
                self._session.add(
                    PieceConditionLinkORM(piece_id=orm_piece.id, condition_id=condition_id)
                )
            await self._session.flush()
            await self._session.refresh(orm_piece, attribute_names=["conditions", "measurements"])
            created.append(orm_piece)
        return [_to_piece(orm) for orm in created]

    async def get(self, piece_id: UUID) -> Piece | None:
        orm_piece = await self._session.get(PieceORM, piece_id)
        return _to_piece(orm_piece) if orm_piece else None

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
        query = select(PieceORM).where(PieceORM.project_id == project_id)
        if part_number_id is not None:
            query = query.where(PieceORM.part_number_id == part_number_id)
        if status is not None:
            query = query.where(PieceORM.overall_status == status)
        if location_id is not None:
            query = query.where(PieceORM.location_id == location_id)
        if condition_ids:
            distinct_matched = func.count(func.distinct(PieceConditionLinkORM.condition_id))
            matching_ids = (
                select(PieceConditionLinkORM.piece_id)
                .where(PieceConditionLinkORM.condition_id.in_(condition_ids))
                .group_by(PieceConditionLinkORM.piece_id)
                .having(distinct_matched == len(condition_ids))
            )
            query = query.where(PieceORM.id.in_(matching_ids))
        if measurement_type_id is not None:
            query = query.join(
                PieceMeasurementORM, PieceMeasurementORM.piece_id == PieceORM.id
            ).where(PieceMeasurementORM.measurement_type_id == measurement_type_id)
            if measurement_min is not None:
                query = query.where(PieceMeasurementORM.value >= measurement_min)
            if measurement_max is not None:
                query = query.where(PieceMeasurementORM.value <= measurement_max)
        query = query.order_by(PieceORM.tracking_number)
        result = await self._session.execute(query)
        return [_to_piece(row) for row in result.scalars().unique().all()]

    async def _get_or_raise(self, piece_id: UUID) -> PieceORM:
        orm_piece = await self._session.get(PieceORM, piece_id)
        if orm_piece is None:
            raise ValueError(f"piece {piece_id} not found")
        return orm_piece

    async def update(
        self,
        piece_id: UUID,
        *,
        overall_status: PieceStatus,
        location_id: UUID | None,
        notes: str | None,
        condition_ids: list[UUID],
    ) -> Piece:
        orm_piece = await self._get_or_raise(piece_id)
        orm_piece.overall_status = overall_status
        orm_piece.location_id = location_id
        orm_piece.notes = notes
        await self._session.execute(
            delete(PieceConditionLinkORM).where(PieceConditionLinkORM.piece_id == piece_id)
        )
        for condition_id in condition_ids:
            self._session.add(
                PieceConditionLinkORM(piece_id=piece_id, condition_id=condition_id)
            )
        await self._session.flush()
        await self._session.refresh(orm_piece, attribute_names=["conditions", "measurements"])
        return _to_piece(orm_piece)

    async def set_measurement(
        self, piece_id: UUID, measurement_type_id: UUID, value: Decimal
    ) -> Piece:
        orm_piece = await self._get_or_raise(piece_id)
        result = await self._session.execute(
            select(PieceMeasurementORM).where(
                PieceMeasurementORM.piece_id == piece_id,
                PieceMeasurementORM.measurement_type_id == measurement_type_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            existing.value = value
        else:
            self._session.add(
                PieceMeasurementORM(
                    piece_id=piece_id, measurement_type_id=measurement_type_id, value=value
                )
            )
        await self._session.flush()
        await self._session.refresh(orm_piece, attribute_names=["measurements"])
        return _to_piece(orm_piece)
