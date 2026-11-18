from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models_checklists import (
    ChecklistItemORM,
    ProjectChecklistORM,
    TaskChecklistItemStateORM,
    TaskChecklistORM,
)
from ops_platform.domain.entities import (
    ChecklistItem,
    ProjectChecklist,
    TaskChecklist,
    TaskChecklistItem,
)
from ops_platform.domain.ports.checklist_repository import ChecklistRepository


class SqlAlchemyChecklistRepository(ChecklistRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _items(self, checklist_id: UUID) -> list[ChecklistItem]:
        rows = await self._session.scalars(
            select(ChecklistItemORM)
            .where(ChecklistItemORM.checklist_id == checklist_id)
            .order_by(ChecklistItemORM.position, ChecklistItemORM.id)
        )
        return [
            ChecklistItem(
                id=row.id,
                checklist_id=row.checklist_id,
                content=row.content,
                position=row.position,
            )
            for row in rows
        ]

    async def _entity(self, row: ProjectChecklistORM) -> ProjectChecklist:
        return ProjectChecklist(
            id=row.id,
            project_id=row.project_id,
            name=row.name,
            created_at=row.created_at,
            items=await self._items(row.id),
        )

    async def create(self, project_id: UUID, name: str) -> ProjectChecklist:
        row = ProjectChecklistORM(project_id=project_id, name=name)
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return await self._entity(row)

    async def get(self, checklist_id: UUID) -> ProjectChecklist | None:
        row = await self._session.get(ProjectChecklistORM, checklist_id)
        return await self._entity(row) if row else None

    async def list_for_project(self, project_id: UUID) -> list[ProjectChecklist]:
        rows = await self._session.scalars(
            select(ProjectChecklistORM)
            .where(ProjectChecklistORM.project_id == project_id)
            .order_by(ProjectChecklistORM.name)
        )
        return [await self._entity(row) for row in rows]

    async def update_name(self, checklist_id: UUID, name: str) -> ProjectChecklist:
        row = await self._session.get(ProjectChecklistORM, checklist_id)
        if row is None:
            raise ValueError("Checklist not found")
        row.name = name
        await self._session.flush()
        return await self._entity(row)

    async def delete(self, checklist_id: UUID) -> None:
        row = await self._session.get(ProjectChecklistORM, checklist_id)
        if row is not None:
            await self._session.delete(row)
            await self._session.flush()

    async def add_item(self, checklist_id: UUID, content: str) -> ChecklistItem:
        position = await self._session.scalar(
            select(func.coalesce(func.max(ChecklistItemORM.position), -1) + 1).where(
                ChecklistItemORM.checklist_id == checklist_id
            )
        )
        row = ChecklistItemORM(checklist_id=checklist_id, content=content, position=position or 0)
        self._session.add(row)
        await self._session.flush()
        return ChecklistItem(
            id=row.id, checklist_id=row.checklist_id, content=row.content, position=row.position
        )

    async def update_item(self, item_id: UUID, content: str) -> ChecklistItem:
        row = await self._session.get(ChecklistItemORM, item_id)
        if row is None:
            raise ValueError("Checklist item not found")
        row.content = content
        await self._session.flush()
        return ChecklistItem(
            id=row.id, checklist_id=row.checklist_id, content=row.content, position=row.position
        )

    async def delete_item(self, item_id: UUID) -> None:
        row = await self._session.get(ChecklistItemORM, item_id)
        if row is not None:
            await self._session.delete(row)
            await self._session.flush()

    async def list_for_task(self, task_id: UUID) -> list[TaskChecklist]:
        checklist_rows = await self._session.scalars(
            select(ProjectChecklistORM)
            .join(TaskChecklistORM, TaskChecklistORM.checklist_id == ProjectChecklistORM.id)
            .where(TaskChecklistORM.task_id == task_id)
            .order_by(ProjectChecklistORM.name)
        )
        state_rows = await self._session.scalars(
            select(TaskChecklistItemStateORM).where(TaskChecklistItemStateORM.task_id == task_id)
        )
        states = {row.item_id: row.completed for row in state_rows}
        result = []
        for checklist in checklist_rows:
            items = await self._items(checklist.id)
            result.append(
                TaskChecklist(
                    id=checklist.id,
                    project_id=checklist.project_id,
                    name=checklist.name,
                    items=[
                        TaskChecklistItem(
                            id=item.id,
                            checklist_id=item.checklist_id,
                            content=item.content,
                            position=item.position,
                            completed=states.get(item.id, False),
                        )
                        for item in items
                    ],
                )
            )
        return result

    async def attach_to_task(self, task_id: UUID, checklist_id: UUID) -> TaskChecklist:
        existing = await self._session.get(TaskChecklistORM, (task_id, checklist_id))
        if existing is None:
            self._session.add(TaskChecklistORM(task_id=task_id, checklist_id=checklist_id))
            await self._session.flush()
        return next(item for item in await self.list_for_task(task_id) if item.id == checklist_id)

    async def detach_from_task(self, task_id: UUID, checklist_id: UUID) -> None:
        item_ids = select(ChecklistItemORM.id).where(ChecklistItemORM.checklist_id == checklist_id)
        await self._session.execute(
            delete(TaskChecklistItemStateORM).where(
                TaskChecklistItemStateORM.task_id == task_id,
                TaskChecklistItemStateORM.item_id.in_(item_ids),
            )
        )
        await self._session.execute(
            delete(TaskChecklistORM).where(
                TaskChecklistORM.task_id == task_id,
                TaskChecklistORM.checklist_id == checklist_id,
            )
        )
        await self._session.flush()

    async def set_item_completed(
        self, task_id: UUID, item_id: UUID, completed: bool
    ) -> TaskChecklist:
        state = await self._session.get(TaskChecklistItemStateORM, (task_id, item_id))
        if state is None:
            self._session.add(
                TaskChecklistItemStateORM(task_id=task_id, item_id=item_id, completed=completed)
            )
        else:
            state.completed = completed
        await self._session.flush()
        item = await self._session.get(ChecklistItemORM, item_id)
        if item is None:
            raise ValueError("Checklist item not found")
        return next(
            checklist
            for checklist in await self.list_for_task(task_id)
            if checklist.id == item.checklist_id
        )
