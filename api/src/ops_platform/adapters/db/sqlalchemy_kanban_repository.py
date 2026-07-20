from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models_issues import KanbanBoardORM, KanbanColumnORM
from ops_platform.domain.entities import IssueStatus, KanbanBoard, KanbanColumn
from ops_platform.domain.ports.kanban_repository import KanbanRepository

# Fixed default columns - see docs/architecture/adr/0004-issue-hierarchy-linking.md
# for why these aren't customizable in this phase.
_DEFAULT_COLUMNS: list[tuple[str, IssueStatus]] = [
    ("Backlog", IssueStatus.BACKLOG),
    ("To Do", IssueStatus.TODO),
    ("In Progress", IssueStatus.IN_PROGRESS),
    ("In Review", IssueStatus.IN_REVIEW),
    ("Done", IssueStatus.DONE),
]


def _to_column(orm_column: KanbanColumnORM) -> KanbanColumn:
    return KanbanColumn(
        id=orm_column.id,
        board_id=orm_column.board_id,
        name=orm_column.name,
        order_index=orm_column.order_index,
        maps_to_status=orm_column.maps_to_status,
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

    async def create_default_board(self, project_id: UUID) -> KanbanBoard:
        orm_board = KanbanBoardORM(project_id=project_id, name="Board")
        self._session.add(orm_board)
        await self._session.flush()

        for order_index, (name, maps_to_status) in enumerate(_DEFAULT_COLUMNS):
            self._session.add(
                KanbanColumnORM(
                    board_id=orm_board.id,
                    name=name,
                    order_index=order_index,
                    maps_to_status=maps_to_status,
                )
            )
        await self._session.flush()
        await self._session.refresh(orm_board, attribute_names=["columns"])
        return _to_entity(orm_board)

    async def get_for_project(self, project_id: UUID) -> KanbanBoard | None:
        result = await self._session.execute(
            select(KanbanBoardORM).where(KanbanBoardORM.project_id == project_id)
        )
        orm_board = result.scalar_one_or_none()
        return _to_entity(orm_board) if orm_board else None
