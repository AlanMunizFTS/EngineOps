from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models_tasks import KanbanBoardORM, KanbanColumnORM
from ops_platform.domain.entities import KanbanBoard, KanbanColumn, TaskStatus
from ops_platform.domain.ports.kanban_repository import KanbanRepository

# Fixed default columns seeded on project creation - see
# docs/architecture/adr/0010-dynamic-kanban-boards.md. Users can rename,
# remap, delete, and add to these freely afterward.
_DEFAULT_COLUMNS: list[tuple[str, TaskStatus]] = [
    ("Backlog", TaskStatus.BACKLOG),
    ("To Do", TaskStatus.TODO),
    ("In Progress", TaskStatus.IN_PROGRESS),
    ("In Review", TaskStatus.IN_REVIEW),
    ("Done", TaskStatus.DONE),
]


def _to_column(orm_column: KanbanColumnORM) -> KanbanColumn:
    return KanbanColumn(
        id=orm_column.id,
        board_id=orm_column.board_id,
        name=orm_column.name,
        order_index=orm_column.order_index,
        maps_to_statuses=list(orm_column.maps_to_statuses),
    )


def _to_entity(orm_board: KanbanBoardORM) -> KanbanBoard:
    return KanbanBoard(
        id=orm_board.id,
        project_id=orm_board.project_id,
        name=orm_board.name,
        columns=[_to_column(column) for column in orm_board.columns],
    )


class SqlAlchemyKanbanRepository(KanbanRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _get_board_or_raise(self, board_id: UUID) -> KanbanBoardORM:
        orm_board = await self._session.get(KanbanBoardORM, board_id)
        if orm_board is None:
            raise ValueError(f"kanban board {board_id} not found")
        return orm_board

    async def _get_column_or_raise(self, column_id: UUID) -> KanbanColumnORM:
        orm_column = await self._session.get(KanbanColumnORM, column_id)
        if orm_column is None:
            raise ValueError(f"kanban column {column_id} not found")
        return orm_column

    async def create_default_board(self, project_id: UUID) -> KanbanBoard:
        orm_board = KanbanBoardORM(project_id=project_id, name="Board")
        self._session.add(orm_board)
        await self._session.flush()

        for order_index, (name, status) in enumerate(_DEFAULT_COLUMNS):
            self._session.add(
                KanbanColumnORM(
                    board_id=orm_board.id,
                    name=name,
                    order_index=order_index,
                    maps_to_statuses=[status],
                )
            )
        await self._session.flush()
        await self._session.refresh(orm_board, attribute_names=["columns"])
        return _to_entity(orm_board)

    async def create_board(self, project_id: UUID, name: str) -> KanbanBoard:
        """Seeds the same 5 default columns as `create_default_board` - a new
        board is immediately useful (every existing task lands somewhere)
        rather than starting as a blank slate the user must configure before
        anything shows up. Freely rename/remap/delete/add from there."""
        orm_board = KanbanBoardORM(project_id=project_id, name=name)
        self._session.add(orm_board)
        await self._session.flush()

        for order_index, (col_name, status) in enumerate(_DEFAULT_COLUMNS):
            self._session.add(
                KanbanColumnORM(
                    board_id=orm_board.id,
                    name=col_name,
                    order_index=order_index,
                    maps_to_statuses=[status],
                )
            )
        await self._session.flush()
        await self._session.refresh(orm_board, attribute_names=["columns"])
        return _to_entity(orm_board)

    async def get(self, board_id: UUID) -> KanbanBoard | None:
        orm_board = await self._session.get(KanbanBoardORM, board_id)
        return _to_entity(orm_board) if orm_board else None

    async def list_for_project(self, project_id: UUID) -> list[KanbanBoard]:
        result = await self._session.execute(
            select(KanbanBoardORM)
            .where(KanbanBoardORM.project_id == project_id)
            .order_by(KanbanBoardORM.name)
        )
        return [_to_entity(row) for row in result.scalars().all()]

    async def rename_board(self, board_id: UUID, name: str) -> KanbanBoard:
        orm_board = await self._get_board_or_raise(board_id)
        orm_board.name = name
        await self._session.flush()
        await self._session.refresh(orm_board, attribute_names=["columns"])
        return _to_entity(orm_board)

    async def delete_board(self, board_id: UUID) -> None:
        orm_board = await self._get_board_or_raise(board_id)
        await self._session.delete(orm_board)
        await self._session.flush()

    async def get_column(self, column_id: UUID) -> KanbanColumn | None:
        orm_column = await self._session.get(KanbanColumnORM, column_id)
        return _to_column(orm_column) if orm_column else None

    async def create_column(
        self, board_id: UUID, name: str, maps_to_statuses: list[TaskStatus]
    ) -> KanbanColumn:
        orm_board = await self._get_board_or_raise(board_id)
        next_index = len(orm_board.columns)
        orm_column = KanbanColumnORM(
            board_id=board_id,
            name=name,
            order_index=next_index,
            maps_to_statuses=maps_to_statuses,
        )
        self._session.add(orm_column)
        await self._session.flush()
        await self._session.refresh(orm_column)
        return _to_column(orm_column)

    async def update_column(
        self, column_id: UUID, name: str, maps_to_statuses: list[TaskStatus]
    ) -> KanbanColumn:
        orm_column = await self._get_column_or_raise(column_id)
        orm_column.name = name
        orm_column.maps_to_statuses = maps_to_statuses
        await self._session.flush()
        await self._session.refresh(orm_column)
        return _to_column(orm_column)

    async def delete_column(self, column_id: UUID) -> None:
        orm_column = await self._get_column_or_raise(column_id)
        await self._session.delete(orm_column)
        await self._session.flush()

    async def reorder_columns(self, board_id: UUID, ordered_column_ids: list[UUID]) -> KanbanBoard:
        orm_board = await self._get_board_or_raise(board_id)
        columns_by_id = {column.id: column for column in orm_board.columns}
        for index, column_id in enumerate(ordered_column_ids):
            if column_id not in columns_by_id:
                raise ValueError(f"column {column_id} does not belong to board {board_id}")
            columns_by_id[column_id].order_index = index
        await self._session.flush()
        await self._session.refresh(orm_board, attribute_names=["columns"])
        return _to_entity(orm_board)
