from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from ops_platform.domain.entities import (
    ChecklistItem,
    ProjectChecklist,
    TaskChecklist,
    TaskChecklistItem,
)
from ops_platform.domain.ports.checklist_repository import ChecklistRepository


class FakeChecklistRepository(ChecklistRepository):
    def __init__(self) -> None:
        self.checklists: dict[UUID, ProjectChecklist] = {}
        self.attachments: set[tuple[UUID, UUID]] = set()
        self.states: dict[tuple[UUID, UUID], bool] = {}

    async def create(self, project_id: UUID, name: str) -> ProjectChecklist:
        checklist = ProjectChecklist(
            id=uuid.uuid4(), project_id=project_id, name=name, created_at=datetime.now(UTC)
        )
        self.checklists[checklist.id] = checklist
        return checklist

    async def get(self, checklist_id: UUID) -> ProjectChecklist | None:
        return self.checklists.get(checklist_id)

    async def list_for_project(self, project_id: UUID) -> list[ProjectChecklist]:
        return [item for item in self.checklists.values() if item.project_id == project_id]

    async def update_name(self, checklist_id: UUID, name: str) -> ProjectChecklist:
        updated = replace(self.checklists[checklist_id], name=name)
        self.checklists[checklist_id] = updated
        return updated

    async def delete(self, checklist_id: UUID) -> None:
        self.checklists.pop(checklist_id, None)
        self.attachments = {item for item in self.attachments if item[1] != checklist_id}

    async def add_item(self, checklist_id: UUID, content: str) -> ChecklistItem:
        checklist = self.checklists[checklist_id]
        item = ChecklistItem(
            id=uuid.uuid4(),
            checklist_id=checklist_id,
            content=content,
            position=len(checklist.items),
        )
        self.checklists[checklist_id] = replace(checklist, items=[*checklist.items, item])
        return item

    async def update_item(self, item_id: UUID, content: str) -> ChecklistItem:
        for checklist_id, checklist in self.checklists.items():
            for item in checklist.items:
                if item.id == item_id:
                    updated = replace(item, content=content)
                    self.checklists[checklist_id] = replace(
                        checklist,
                        items=[
                            updated if value.id == item_id else value for value in checklist.items
                        ],
                    )
                    return updated
        raise ValueError("Checklist item not found")

    async def delete_item(self, item_id: UUID) -> None:
        for checklist_id, checklist in self.checklists.items():
            self.checklists[checklist_id] = replace(
                checklist, items=[item for item in checklist.items if item.id != item_id]
            )

    async def list_for_task(self, task_id: UUID) -> list[TaskChecklist]:
        result = []
        for attached_task_id, checklist_id in self.attachments:
            if attached_task_id != task_id or checklist_id not in self.checklists:
                continue
            checklist = self.checklists[checklist_id]
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
                            completed=self.states.get((task_id, item.id), False),
                        )
                        for item in checklist.items
                    ],
                )
            )
        return result

    async def attach_to_task(self, task_id: UUID, checklist_id: UUID) -> TaskChecklist:
        self.attachments.add((task_id, checklist_id))
        return next(item for item in await self.list_for_task(task_id) if item.id == checklist_id)

    async def detach_from_task(self, task_id: UUID, checklist_id: UUID) -> None:
        self.attachments.discard((task_id, checklist_id))

    async def set_item_completed(
        self, task_id: UUID, item_id: UUID, completed: bool
    ) -> TaskChecklist:
        self.states[(task_id, item_id)] = completed
        return next(
            checklist
            for checklist in await self.list_for_task(task_id)
            if any(item.id == item_id for item in checklist.items)
        )
