from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models import AreaStatusORM, ImplementationORM
from ops_platform.domain.entities import AreaStatus, Implementation, ImplementationStatus
from ops_platform.domain.ports.implementation_repository import ImplementationRepository


def _to_phase_status(orm_status: AreaStatusORM | None) -> AreaStatus | None:
    if orm_status is None:
        return None
    return AreaStatus(
        id=orm_status.id,
        area_type_id=orm_status.area_type_id,
        name=orm_status.name,
        sort_order=orm_status.sort_order,
    )


def _to_entity(orm_impl: ImplementationORM) -> Implementation:
    return Implementation(
        id=orm_impl.id,
        machine_id=orm_impl.machine_id,
        label=orm_impl.label,
        status=orm_impl.status,
        superseded_by=orm_impl.superseded_by,
        created_at=orm_impl.created_at,
        phase_status=_to_phase_status(orm_impl.phase_status),
    )


class SqlAlchemyImplementationRepository(ImplementationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, machine_id: UUID, label: str, status: ImplementationStatus
    ) -> Implementation:
        orm_impl = ImplementationORM(machine_id=machine_id, label=label, status=status)
        self._session.add(orm_impl)
        await self._session.flush()
        await self._session.refresh(orm_impl)
        return _to_entity(orm_impl)

    async def get(self, implementation_id: UUID) -> Implementation | None:
        orm_impl = await self._session.get(ImplementationORM, implementation_id)
        return _to_entity(orm_impl) if orm_impl else None

    async def list_for_machine(self, machine_id: UUID) -> list[Implementation]:
        result = await self._session.execute(
            select(ImplementationORM)
            .where(ImplementationORM.machine_id == machine_id)
            .order_by(ImplementationORM.created_at)
        )
        return [_to_entity(row) for row in result.scalars().all()]

    async def supersede(self, implementation_id: UUID, superseded_by: UUID) -> Implementation:
        orm_impl = await self._session.get(ImplementationORM, implementation_id)
        if orm_impl is None:
            raise ValueError(f"implementation {implementation_id} not found")

        orm_impl.status = ImplementationStatus.SUPERSEDED
        orm_impl.superseded_by = superseded_by
        await self._session.flush()
        await self._session.refresh(orm_impl)
        return _to_entity(orm_impl)

    async def update_phase(
        self, implementation_id: UUID, status_id: UUID | None
    ) -> Implementation:
        orm_impl = await self._session.get(ImplementationORM, implementation_id)
        if orm_impl is None:
            raise ValueError(f"implementation {implementation_id} not found")
        orm_impl.phase_status_id = status_id
        await self._session.flush()
        await self._session.refresh(orm_impl, attribute_names=["phase_status"])
        return _to_entity(orm_impl)
