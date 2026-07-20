from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models_issues import MilestoneORM
from ops_platform.domain.entities import Milestone, MilestoneStatus
from ops_platform.domain.ports.milestone_repository import MilestoneRepository


def _to_entity(orm_milestone: MilestoneORM) -> Milestone:
    return Milestone(
        id=orm_milestone.id,
        project_id=orm_milestone.project_id,
        title=orm_milestone.title,
        description=orm_milestone.description,
        due_date=orm_milestone.due_date,
        status=orm_milestone.status,
        created_at=orm_milestone.created_at,
    )


class SqlAlchemyMilestoneRepository(MilestoneRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, project_id: UUID, title: str, description: str | None, due_date: date | None
    ) -> Milestone:
        orm_milestone = MilestoneORM(
            project_id=project_id, title=title, description=description, due_date=due_date
        )
        self._session.add(orm_milestone)
        await self._session.flush()
        await self._session.refresh(orm_milestone)
        return _to_entity(orm_milestone)

    async def get(self, milestone_id: UUID) -> Milestone | None:
        orm_milestone = await self._session.get(MilestoneORM, milestone_id)
        return _to_entity(orm_milestone) if orm_milestone else None

    async def list_for_project(self, project_id: UUID) -> list[Milestone]:
        result = await self._session.execute(
            select(MilestoneORM)
            .where(MilestoneORM.project_id == project_id)
            .order_by(MilestoneORM.created_at)
        )
        return [_to_entity(row) for row in result.scalars().all()]

    async def update_status(self, milestone_id: UUID, status: MilestoneStatus) -> Milestone:
        orm_milestone = await self._session.get(MilestoneORM, milestone_id)
        if orm_milestone is None:
            raise ValueError(f"milestone {milestone_id} not found")
        orm_milestone.status = status
        await self._session.flush()
        await self._session.refresh(orm_milestone)
        return _to_entity(orm_milestone)
