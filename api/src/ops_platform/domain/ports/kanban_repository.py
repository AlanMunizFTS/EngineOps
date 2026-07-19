from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ops_platform.domain.entities import KanbanBoard


class KanbanRepository(ABC):
    """Port for the per-project kanban board. Columns are fixed (5, mirroring
    IssueStatus) rather than customizable in this phase - see
    docs/architecture/adr/0004-issue-hierarchy-linking.md."""

    @abstractmethod
    async def create_default_board(self, project_id: UUID) -> KanbanBoard:
        """Creates the board and seeds its 5 fixed columns. Called once per
        project, from the project-creation flow (and via a one-time backfill
        migration for projects that predate this table)."""
        ...

    @abstractmethod
    async def get_for_project(self, project_id: UUID) -> KanbanBoard | None: ...
