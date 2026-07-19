from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models_issues import LabelORM
from ops_platform.domain.entities import Label
from ops_platform.domain.ports.label_repository import LabelRepository


def _to_entity(orm_label: LabelORM) -> Label:
    return Label(
        id=orm_label.id,
        project_id=orm_label.project_id,
        name=orm_label.name,
        color=orm_label.color,
    )


class SqlAlchemyLabelRepository(LabelRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, project_id: UUID, name: str, color: str) -> Label:
        orm_label = LabelORM(project_id=project_id, name=name, color=color)
        self._session.add(orm_label)
        await self._session.flush()
        await self._session.refresh(orm_label)
        return _to_entity(orm_label)

    async def get(self, label_id: UUID) -> Label | None:
        orm_label = await self._session.get(LabelORM, label_id)
        return _to_entity(orm_label) if orm_label else None

    async def list_for_project(self, project_id: UUID) -> list[Label]:
        result = await self._session.execute(
            select(LabelORM).where(LabelORM.project_id == project_id).order_by(LabelORM.name)
        )
        return [_to_entity(row) for row in result.scalars().all()]
