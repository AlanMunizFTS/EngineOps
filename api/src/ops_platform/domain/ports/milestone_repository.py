from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from ops_platform.domain.entities import Milestone, MilestoneStatus


class MilestoneRepository(ABC):
    """Port for milestone persistence. A milestone always belongs to exactly one
    project; its progress (% of linked issues closed) is a read-model computed
    in the router from IssueRepository.list_for_project, not stored here."""

    @abstractmethod
    async def create(
        self, project_id: UUID, title: str, description: str | None, due_date: date | None
    ) -> Milestone: ...

    @abstractmethod
    async def get(self, milestone_id: UUID) -> Milestone | None: ...

    @abstractmethod
    async def list_for_project(self, project_id: UUID) -> list[Milestone]: ...

    @abstractmethod
    async def update_status(self, milestone_id: UUID, status: MilestoneStatus) -> Milestone: ...
