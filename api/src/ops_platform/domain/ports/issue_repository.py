from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from ops_platform.domain.entities import Issue, IssuePriority, IssueStatus, IssueType


class IssueRepository(ABC):
    """Port for issue persistence, including its label associations (issue_labels
    join table) and status transitions."""

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
        assignee_id: UUID | None,
        parent_issue_id: UUID | None = None,
        start_date: date | None = None,
        due_date: date | None = None,
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
        assignee_id: UUID | None,
        parent_issue_id: UUID | None = None,
        start_date: date | None = None,
        due_date: date | None = None,
        closed_at: date | None = None,
    ) -> Issue:
        """`closed_at` here is a manual correction (e.g. backfilling a close
        date) - separate from the automatic stamping `set_status` does when
        an issue actually moves to/from DONE.

        `parent_assigned_at` is not a caller-supplied field: the
        implementation stamps it internally whenever the resolved
        `parent_issue_id` differs from what's currently stored (set on
        change to a parent, cleared on change to None), the same
        "caller doesn't manage this" pattern `set_status` uses for
        `closed_at`."""
        ...

    @abstractmethod
    async def set_status(self, issue_id: UUID, status: IssueStatus) -> Issue:
        """Sets `status`. Also sets `closed_at` when moving to DONE, and clears
        it when moving away from DONE - the caller doesn't manage that field."""
        ...

    @abstractmethod
    async def attach_label(self, issue_id: UUID, label_id: UUID) -> Issue: ...

    @abstractmethod
    async def detach_label(self, issue_id: UUID, label_id: UUID) -> Issue: ...

    @abstractmethod
    async def delete(self, issue_id: UUID) -> None: ...
