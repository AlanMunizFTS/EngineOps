from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ops_platform.domain.entities import ChecklistItem, ProjectChecklist, TaskChecklist


class ChecklistRepository(ABC):
    @abstractmethod
    async def create(self, project_id: UUID, name: str) -> ProjectChecklist: ...

    @abstractmethod
    async def get(self, checklist_id: UUID) -> ProjectChecklist | None: ...

    @abstractmethod
    async def list_for_project(self, project_id: UUID) -> list[ProjectChecklist]: ...

    @abstractmethod
    async def update_name(self, checklist_id: UUID, name: str) -> ProjectChecklist: ...

    @abstractmethod
    async def delete(self, checklist_id: UUID) -> None: ...

    @abstractmethod
    async def add_item(self, checklist_id: UUID, content: str) -> ChecklistItem: ...

    @abstractmethod
    async def update_item(self, item_id: UUID, content: str) -> ChecklistItem: ...

    @abstractmethod
    async def delete_item(self, item_id: UUID) -> None: ...

    @abstractmethod
    async def attach_to_task(self, task_id: UUID, checklist_id: UUID) -> TaskChecklist: ...

    @abstractmethod
    async def detach_from_task(self, task_id: UUID, checklist_id: UUID) -> None: ...

    @abstractmethod
    async def list_for_task(self, task_id: UUID) -> list[TaskChecklist]: ...

    @abstractmethod
    async def set_item_completed(
        self, task_id: UUID, item_id: UUID, completed: bool
    ) -> TaskChecklist: ...
