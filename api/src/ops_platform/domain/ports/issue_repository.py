from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ops_platform.domain.entities import Issue, IssuePriority, IssueStatus, IssueType


class IssueRepository(ABC):
    """Port for issue persistence, including its label associations (issue_labels
    join table) and status transitions. `plant_id`/`machine_id`/`implementation_id`
    are a flexible link into the hierarchy - at most one is set at a time, enforced
    by the router before it reaches this port and backstopped by a DB CHECK
    constraint (see docs/architecture/adr/0004-issue-hierarchy-linking.md)."""

    @abstractmethod
    async def create(
        self,
        *,
        project_id: UUID,
        title: str,
        description: str | None,
        issue_type: IssueType,
        priority: IssuePriority,
        created_by: UUID,
        milestone_id: UUID | None,
        assignee_id: UUID | None,
        plant_id: UUID | None,
        machine_id: UUID | None,
        implementation_id: UUID | None,
    ) -> Issue: ...

    @abstractmethod
    async def get(self, issue_id: UUID) -> Issue | None: ...

    @abstractmethod
    async def list_for_project(
        self,
        project_id: UUID,
        *,
        status: IssueStatus | None = None,
        assignee_id: UUID | None = None,
        label_id: UUID | None = None,
        milestone_id: UUID | None = None,
    ) -> list[Issue]: ...

    @abstractmethod
    async def update(
        self,
        issue_id: UUID,
        *,
        title: str,
        description: str | None,
        priority: IssuePriority,
        issue_type: IssueType,
        milestone_id: UUID | None,
        assignee_id: UUID | None,
        plant_id: UUID | None,
        machine_id: UUID | None,
        implementation_id: UUID | None,
    ) -> Issue: ...

    @abstractmethod
    async def set_status(self, issue_id: UUID, status: IssueStatus) -> Issue:
        """Sets `status`. Also sets `closed_at` when moving to DONE, and clears
        it when moving away from DONE - the caller doesn't manage that field."""
        ...

    @abstractmethod
    async def attach_label(self, issue_id: UUID, label_id: UUID) -> Issue: ...

    @abstractmethod
    async def detach_label(self, issue_id: UUID, label_id: UUID) -> Issue: ...
