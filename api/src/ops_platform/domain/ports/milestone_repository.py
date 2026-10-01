from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any
from uuid import UUID

from ops_platform.domain.entities import Milestone, MilestoneStatus


class MilestoneRepository(ABC):
    @abstractmethod
    async def create(
        self,
        *,
        project_id: UUID,
        title: str,
        description: str | None,
        status: MilestoneStatus,
        due_date: date | None,
    ) -> Milestone: ...

    @abstractmethod
    async def get(self, milestone_id: UUID) -> Milestone | None: ...

    @abstractmethod
    async def list_for_project(self, project_id: UUID) -> list[Milestone]: ...

    @abstractmethod
    async def update(self, milestone_id: UUID, **changes: Any) -> Milestone: ...

    @abstractmethod
    async def delete(self, milestone_id: UUID) -> None: ...
