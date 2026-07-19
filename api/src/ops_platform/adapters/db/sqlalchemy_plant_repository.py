from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models import AreaStatusORM, PlantORM
from ops_platform.domain.entities import AreaStatus, Plant
from ops_platform.domain.ports.plant_repository import PlantRepository


def _to_phase_status(orm_status: AreaStatusORM | None) -> AreaStatus | None:
    if orm_status is None:
        return None
    return AreaStatus(
        id=orm_status.id,
        area_type_id=orm_status.area_type_id,
        name=orm_status.name,
        sort_order=orm_status.sort_order,
    )


def _to_entity(orm_plant: PlantORM) -> Plant:
    return Plant(
        id=orm_plant.id,
        project_id=orm_plant.project_id,
        name=orm_plant.name,
        location=orm_plant.location,
        created_at=orm_plant.created_at,
        phase_status=_to_phase_status(orm_plant.phase_status),
    )


class SqlAlchemyPlantRepository(PlantRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, project_id: UUID, name: str, location: str | None) -> Plant:
        orm_plant = PlantORM(project_id=project_id, name=name, location=location)
        self._session.add(orm_plant)
        await self._session.flush()
        await self._session.refresh(orm_plant)
        return _to_entity(orm_plant)

    async def get(self, plant_id: UUID) -> Plant | None:
        orm_plant = await self._session.get(PlantORM, plant_id)
        return _to_entity(orm_plant) if orm_plant else None

    async def list_for_project(self, project_id: UUID) -> list[Plant]:
        result = await self._session.execute(
            select(PlantORM).where(PlantORM.project_id == project_id).order_by(PlantORM.created_at)
        )
        return [_to_entity(row) for row in result.scalars().all()]

    async def update_phase(self, plant_id: UUID, status_id: UUID | None) -> Plant:
        orm_plant = await self._session.get(PlantORM, plant_id)
        if orm_plant is None:
            raise ValueError(f"plant {plant_id} not found")
        orm_plant.phase_status_id = status_id
        await self._session.flush()
        await self._session.refresh(orm_plant, attribute_names=["phase_status"])
        return _to_entity(orm_plant)
