from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models_tasks import LabelORM, TaskLabelORM, TaskORM
from ops_platform.domain.entities import Label, Task, TaskPriority, TaskStatus, TaskType
from ops_platform.domain.ports.task_repository import TaskRepository


def _to_label(row: LabelORM) -> Label:
    return Label(id=row.id, project_id=row.project_id, name=row.name, color=row.color)


def _to_entity(row: TaskORM, total: int = 0, completed: int = 0) -> Task:
    return Task(
        id=row.id,
        project_id=row.project_id,
        milestone_id=row.milestone_id,
        parent_task_id=row.parent_task_id,
        title=row.title,
        description=row.description,
        status=row.status,
        priority=row.priority,
        task_type=row.task_type,
        assignee_id=row.assignee_id,
        created_by=row.created_by,
        start_date=row.start_date,
        due_date=row.due_date,
        closed_at=row.closed_at,
        parent_assigned_at=row.parent_assigned_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        labels=[_to_label(label) for label in row.labels],
        subtasks_total=total,
        subtasks_completed=completed,
    )


class SqlAlchemyTaskRepository(TaskRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _get_row(self, task_id: UUID) -> TaskORM | None:
        return await self._session.get(TaskORM, task_id)

    async def _get_or_raise(self, task_id: UUID) -> TaskORM:
        row = await self._get_row(task_id)
        if row is None:
            raise ValueError(f"task {task_id} not found")
        return row

    async def _counts(self, task_id: UUID) -> tuple[int, int]:
        result = await self._session.execute(
            select(
                func.count(TaskORM.id),
                func.count(TaskORM.id).filter(TaskORM.status == TaskStatus.DONE),
            ).where(TaskORM.parent_task_id == task_id)
        )
        total, completed = result.one()
        return int(total), int(completed)

    async def _entity(self, row: TaskORM) -> Task:
        total, completed = await self._counts(row.id)
        return _to_entity(row, total, completed)

    async def create(
        self,
        *,
        project_id: UUID,
        title: str,
        description: str | None,
        task_type: TaskType,
        priority: TaskPriority,
        created_by: UUID | None,
        assignee_id: UUID | None,
        milestone_id: UUID | None = None,
        parent_task_id: UUID | None = None,
        start_date: date | None = None,
        due_date: date | None = None,
    ) -> Task:
        row = TaskORM(
            project_id=project_id,
            title=title,
            description=description,
            task_type=task_type,
            priority=priority,
            created_by=created_by,
            assignee_id=assignee_id,
            milestone_id=milestone_id,
            parent_task_id=parent_task_id,
            parent_assigned_at=datetime.now(UTC) if parent_task_id else None,
            start_date=start_date,
            due_date=due_date,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row, attribute_names=["labels", "created_at", "updated_at"])
        return _to_entity(row)

    async def get(self, task_id: UUID) -> Task | None:
        row = await self._get_row(task_id)
        return await self._entity(row) if row else None

    async def list_for_project(
        self,
        project_id: UUID,
        *,
        include_subtasks: bool = False,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        task_type: TaskType | None = None,
        assignee_id: UUID | None = None,
        milestone_id: UUID | None = None,
        label_id: UUID | None = None,
    ) -> list[Task]:
        query = select(TaskORM).where(TaskORM.project_id == project_id)
        if not include_subtasks:
            query = query.where(TaskORM.parent_task_id.is_(None))
        if status is not None:
            query = query.where(TaskORM.status == status)
        if priority is not None:
            query = query.where(TaskORM.priority == priority)
        if task_type is not None:
            query = query.where(TaskORM.task_type == task_type)
        if assignee_id is not None:
            query = query.where(TaskORM.assignee_id == assignee_id)
        if milestone_id is not None:
            query = query.where(TaskORM.milestone_id == milestone_id)
        if label_id is not None:
            query = query.join(TaskLabelORM, TaskLabelORM.task_id == TaskORM.id).where(
                TaskLabelORM.label_id == label_id
            )
        result = await self._session.execute(query.order_by(TaskORM.created_at.desc()))
        return [await self._entity(row) for row in result.scalars().all()]

    async def list_pending_for_assignee(self, assignee_id: UUID) -> list[Task]:
        result = await self._session.execute(
            select(TaskORM)
            .where(
                TaskORM.assignee_id == assignee_id,
                TaskORM.status != TaskStatus.DONE,
                TaskORM.parent_task_id.is_(None),
            )
            .order_by(TaskORM.created_at.desc())
        )
        return [await self._entity(row) for row in result.scalars().all()]

    async def list_subtasks(self, task_id: UUID) -> list[Task]:
        result = await self._session.execute(
            select(TaskORM)
            .where(TaskORM.parent_task_id == task_id)
            .order_by(TaskORM.parent_assigned_at, TaskORM.created_at)
        )
        return [await self._entity(row) for row in result.scalars().all()]

    async def list_by_milestone(self, milestone_id: UUID) -> list[Task]:
        result = await self._session.execute(
            select(TaskORM).where(
                TaskORM.milestone_id == milestone_id, TaskORM.parent_task_id.is_(None)
            )
        )
        return [await self._entity(row) for row in result.scalars().all()]

    async def has_children(self, task_id: UUID) -> bool:
        value = await self._session.scalar(
            select(func.count(TaskORM.id)).where(TaskORM.parent_task_id == task_id)
        )
        return bool(value)

    async def update(self, task_id: UUID, **changes: Any) -> Task:
        row = await self._get_or_raise(task_id)
        allowed = {
            "title",
            "description",
            "priority",
            "task_type",
            "assignee_id",
            "milestone_id",
            "start_date",
            "due_date",
            "closed_at",
        }
        for field, value in changes.items():
            if field not in allowed:
                raise ValueError(f"unsupported task field: {field}")
            if (
                field == "closed_at"
                and isinstance(value, date)
                and not isinstance(value, datetime)
            ):
                value = datetime.combine(value, datetime.min.time(), tzinfo=UTC)
            setattr(row, field, value)
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(row, attribute_names=["labels"])
        return await self._entity(row)

    async def set_status(self, task_id: UUID, status: TaskStatus) -> Task:
        row = await self._get_or_raise(task_id)
        row.status = status
        row.closed_at = datetime.now(UTC) if status == TaskStatus.DONE else None
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(row, attribute_names=["labels"])
        return await self._entity(row)

    async def reparent(self, task_id: UUID, parent_task_id: UUID | None) -> Task:
        row = await self._get_or_raise(task_id)
        if row.parent_task_id != parent_task_id:
            row.parent_assigned_at = datetime.now(UTC) if parent_task_id else None
        row.parent_task_id = parent_task_id
        row.milestone_id = None
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(row, attribute_names=["labels"])
        return await self._entity(row)

    async def attach_label(self, task_id: UUID, label_id: UUID) -> Task:
        row = await self._get_or_raise(task_id)
        if not any(label.id == label_id for label in row.labels):
            self._session.add(TaskLabelORM(task_id=task_id, label_id=label_id))
            await self._session.flush()
            await self._session.refresh(row, attribute_names=["labels"])
        return await self._entity(row)

    async def detach_label(self, task_id: UUID, label_id: UUID) -> Task:
        row = await self._get_or_raise(task_id)
        await self._session.execute(
            delete(TaskLabelORM).where(
                TaskLabelORM.task_id == task_id, TaskLabelORM.label_id == label_id
            )
        )
        await self._session.flush()
        await self._session.refresh(row, attribute_names=["labels"])
        return await self._entity(row)

    async def delete(self, task_id: UUID) -> None:
        await self._session.delete(await self._get_or_raise(task_id))
        await self._session.flush()
