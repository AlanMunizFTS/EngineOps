from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models import AreaStatusORM, MachineORM
from ops_platform.domain.entities import AreaStatus, Machine
from ops_platform.domain.ports.machine_repository import MachineRepository


def _to_phase_status(orm_status: AreaStatusORM | None) -> AreaStatus | None:
    if orm_status is None:
        return None
    return AreaStatus(
        id=orm_status.id,
        area_type_id=orm_status.area_type_id,
        name=orm_status.name,
        sort_order=orm_status.sort_order,
    )


def _to_entity(orm_machine: MachineORM) -> Machine:
    return Machine(
        id=orm_machine.id,
        plant_id=orm_machine.plant_id,
        name=orm_machine.name,
        machine_type=orm_machine.machine_type,
        location=orm_machine.location,
        created_at=orm_machine.created_at,
        phase_status=_to_phase_status(orm_machine.phase_status),
    )


class SqlAlchemyMachineRepository(MachineRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, plant_id: UUID, name: str, machine_type: str | None, location: str | None
    ) -> Machine:
        orm_machine = MachineORM(
            plant_id=plant_id, name=name, machine_type=machine_type, location=location
        )
        self._session.add(orm_machine)
        await self._session.flush()
        await self._session.refresh(orm_machine)
        return _to_entity(orm_machine)

    async def get(self, machine_id: UUID) -> Machine | None:
        orm_machine = await self._session.get(MachineORM, machine_id)
        return _to_entity(orm_machine) if orm_machine else None

    async def list_for_plant(self, plant_id: UUID) -> list[Machine]:
        result = await self._session.execute(
            select(MachineORM)
            .where(MachineORM.plant_id == plant_id)
            .order_by(MachineORM.created_at)
        )
        return [_to_entity(row) for row in result.scalars().all()]

    async def update_phase(self, machine_id: UUID, status_id: UUID | None) -> Machine:
        orm_machine = await self._session.get(MachineORM, machine_id)
        if orm_machine is None:
            raise ValueError(f"machine {machine_id} not found")
        orm_machine.phase_status_id = status_id
        await self._session.flush()
        await self._session.refresh(orm_machine, attribute_names=["phase_status"])
        return _to_entity(orm_machine)
