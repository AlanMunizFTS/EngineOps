from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any
from uuid import UUID

from ops_platform.domain.entities import Task, TaskPriority, TaskStatus, TaskType


class TaskRepository(ABC):
    @abstractmethod
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
        assignee_ids: list[UUID] | None = None,
        milestone_id: UUID | None = None,
        parent_task_id: UUID | None = None,
        start_date: date | None = None,
        due_date: date | None = None,
    ) -> Task: ...

    @abstractmethod
    async def get(self, task_id: UUID) -> Task | None: ...

    @abstractmethod
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
    ) -> list[Task]: ...

    @abstractmethod
    async def list_pending_for_assignee(self, assignee_id: UUID) -> list[Task]: ...

    @abstractmethod
    async def list_subtasks(self, task_id: UUID) -> list[Task]: ...

    @abstractmethod
    async def list_by_milestone(self, milestone_id: UUID) -> list[Task]: ...

    @abstractmethod
    async def has_children(self, task_id: UUID) -> bool: ...

    @abstractmethod
    async def update(self, task_id: UUID, **changes: Any) -> Task: ...

    @abstractmethod
    async def set_status(self, task_id: UUID, status: TaskStatus) -> Task: ...

    @abstractmethod
    async def reparent(self, task_id: UUID, parent_task_id: UUID | None) -> Task: ...

    @abstractmethod
    async def attach_label(self, task_id: UUID, label_id: UUID) -> Task: ...

    @abstractmethod
    async def detach_label(self, task_id: UUID, label_id: UUID) -> Task: ...

    @abstractmethod
    async def delete(self, task_id: UUID) -> None: ...
