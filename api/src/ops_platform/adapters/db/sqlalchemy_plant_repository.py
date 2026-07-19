from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models import PlantORM
from ops_platform.domain.entities import Plant
from ops_platform.domain.ports.plant_repository import PlantRepository


def _to_entity(orm_plant: PlantORM) -> Plant:
    return Plant(
        id=orm_plant.id,
        project_id=orm_plant.project_id,
        name=orm_plant.name,
        location=orm_plant.location,
        created_at=orm_plant.created_at,
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
