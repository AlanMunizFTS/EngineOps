from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models import AreaStatusORM, AreaTypeORM, ProjectAreaORM
from ops_platform.domain.entities import AreaStatus, AreaType, ProjectArea
from ops_platform.domain.ports.area_repository import AreaRepository

_REFRESH_ATTRS = ["area_type", "status", "updated_at"]


def _to_area_type(orm_area_type: AreaTypeORM) -> AreaType:
    return AreaType(
        id=orm_area_type.id, name=orm_area_type.name, description=orm_area_type.description
    )


def _to_area_status(orm_status: AreaStatusORM) -> AreaStatus:
    return AreaStatus(
        id=orm_status.id,
        area_type_id=orm_status.area_type_id,
        name=orm_status.name,
        sort_order=orm_status.sort_order,
    )


def _to_project_area(orm_area: ProjectAreaORM) -> ProjectArea:
    return ProjectArea(
        id=orm_area.id,
        project_id=orm_area.project_id,
        area_type=_to_area_type(orm_area.area_type),
        status=_to_area_status(orm_area.status),
        updated_by=orm_area.updated_by,
        updated_at=orm_area.updated_at,
    )


class SqlAlchemyAreaRepository(AreaRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_area_types(self) -> list[AreaType]:
        result = await self._session.execute(select(AreaTypeORM).order_by(AreaTypeORM.name))
        return [_to_area_type(row) for row in result.scalars().all()]

    async def list_statuses_for_type(self, area_type_id: UUID) -> list[AreaStatus]:
        result = await self._session.execute(
            select(AreaStatusORM)
            .where(AreaStatusORM.area_type_id == area_type_id)
            .order_by(AreaStatusORM.sort_order)
        )
        return [_to_area_status(row) for row in result.scalars().all()]

    async def create_default_areas(self, project_id: UUID) -> list[ProjectArea]:
        area_types = (await self._session.execute(select(AreaTypeORM))).scalars().all()

        orm_areas: list[ProjectAreaORM] = []
        for area_type in area_types:
            default_status = (
                await self._session.execute(
                    select(AreaStatusORM)
                    .where(AreaStatusORM.area_type_id == area_type.id)
                    .order_by(AreaStatusORM.sort_order)
                    .limit(1)
                )
            ).scalar_one()
            orm_area = ProjectAreaORM(
                project_id=project_id, area_type_id=area_type.id, status_id=default_status.id
            )
            self._session.add(orm_area)
            orm_areas.append(orm_area)

        await self._session.flush()
        for orm_area in orm_areas:
            await self._session.refresh(orm_area, attribute_names=_REFRESH_ATTRS)
        return [_to_project_area(orm_area) for orm_area in orm_areas]

    async def list_for_project(self, project_id: UUID) -> list[ProjectArea]:
        result = await self._session.execute(
            select(ProjectAreaORM).where(ProjectAreaORM.project_id == project_id)
        )
        return [_to_project_area(row) for row in result.scalars().all()]

    async def update_status(
        self, project_area_id: UUID, status_id: UUID, updated_by: UUID
    ) -> ProjectArea:
        orm_area = await self._session.get(ProjectAreaORM, project_area_id)
        if orm_area is None:
            raise ValueError(f"project_area {project_area_id} not found")

        orm_area.status_id = status_id
        orm_area.updated_by = updated_by
        await self._session.flush()
        await self._session.refresh(orm_area, attribute_names=_REFRESH_ATTRS)
        return _to_project_area(orm_area)
