from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from ops_platform.domain.entities import IssueStatus, KanbanBoard, KanbanColumn


class KanbanRepository(ABC):
    """Port for a project's kanban boards. A project can have any number of
    boards (docs/architecture/adr/0010-dynamic-kanban-boards.md); each column
    maps to zero or more `IssueStatus` values and card membership is derived
    entirely from that mapping - there's no separate card-placement table."""

    @abstractmethod
    async def create_default_board(self, project_id: UUID) -> KanbanBoard:
        """Creates a board named "Board" and seeds its 5 fixed,
        single-status columns. Called once per project, from the
        project-creation flow."""
        ...

    @abstractmethod
    async def create_board(self, project_id: UUID, name: str) -> KanbanBoard:
        """Seeds the same 5 default status-mapped columns as
        `create_default_board`, so the board shows every existing issue
        immediately rather than starting blank. The caller renames/remaps/
        deletes/adds columns from there via the column methods below."""
        ...

    @abstractmethod
    async def get(self, board_id: UUID) -> KanbanBoard | None: ...

    @abstractmethod
    async def list_for_project(self, project_id: UUID) -> list[KanbanBoard]: ...

    @abstractmethod
    async def rename_board(self, board_id: UUID, name: str) -> KanbanBoard: ...

    @abstractmethod
    async def delete_board(self, board_id: UUID) -> None: ...

    @abstractmethod
    async def get_column(self, column_id: UUID) -> KanbanColumn | None: ...

    @abstractmethod
    async def create_column(
        self, board_id: UUID, name: str, maps_to_statuses: list[IssueStatus]
    ) -> KanbanColumn:
        """Appends the column at the end of the board's column order."""
        ...

    @abstractmethod
    async def update_column(
        self, column_id: UUID, name: str, maps_to_statuses: list[IssueStatus]
    ) -> KanbanColumn: ...

    @abstractmethod
    async def delete_column(self, column_id: UUID) -> None: ...

    @abstractmethod
    async def reorder_columns(self, board_id: UUID, ordered_column_ids: list[UUID]) -> KanbanBoard:
        """Sets `order_index` on each column to its position in
        `ordered_column_ids`. Callers must pass every column_id belonging to
        the board, exactly once."""
        ...
