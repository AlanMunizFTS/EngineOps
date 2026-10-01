from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models_tasks import MilestoneORM, TaskORM
from ops_platform.domain.entities import Milestone, TaskStatus
from ops_platform.domain.ports.milestone_repository import MilestoneRepository


class SqlAlchemyMilestoneRepository(MilestoneRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _entity(self, row: MilestoneORM) -> Milestone:
        result = await self._session.execute(
            select(
                func.count(TaskORM.id),
                func.count(TaskORM.id).filter(TaskORM.status == TaskStatus.DONE),
            ).where(TaskORM.milestone_id == row.id, TaskORM.parent_task_id.is_(None))
        )
        total, completed = result.one()
        return Milestone(
            id=row.id,
            project_id=row.project_id,
            title=row.title,
            description=row.description,
            status=row.status,
            due_date=row.due_date,
            created_at=row.created_at,
            updated_at=row.updated_at,
            total_tasks=int(total),
            completed_tasks=int(completed),
        )

    async def create(self, **values: Any) -> Milestone:
        row = MilestoneORM(**values)
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return await self._entity(row)

    async def get(self, milestone_id: UUID) -> Milestone | None:
        row = await self._session.get(MilestoneORM, milestone_id)
        return await self._entity(row) if row else None

    async def list_for_project(self, project_id: UUID) -> list[Milestone]:
        result = await self._session.execute(
            select(MilestoneORM)
            .where(MilestoneORM.project_id == project_id)
            .order_by(MilestoneORM.created_at.desc())
        )
        return [await self._entity(row) for row in result.scalars().all()]

    async def update(self, milestone_id: UUID, **changes: Any) -> Milestone:
        row = await self._session.get(MilestoneORM, milestone_id)
        if row is None:
            raise ValueError(f"milestone {milestone_id} not found")
        for field, value in changes.items():
            if field not in {"title", "description", "status", "due_date"}:
                raise ValueError(f"unsupported milestone field: {field}")
            setattr(row, field, value)
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        return await self._entity(row)

    async def delete(self, milestone_id: UUID) -> None:
        row = await self._session.get(MilestoneORM, milestone_id)
        if row is None:
            raise ValueError(f"milestone {milestone_id} not found")
        await self._session.delete(row)
        await self._session.flush()
