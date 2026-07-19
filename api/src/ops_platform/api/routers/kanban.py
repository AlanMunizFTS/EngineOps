from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from ops_platform.api.deps import get_kanban_repository, get_project_repository
from ops_platform.domain.entities import KanbanBoard
from ops_platform.domain.ports.kanban_repository import KanbanRepository
from ops_platform.domain.ports.project_repository import ProjectRepository
from ops_platform.schemas.kanban import KanbanBoardResponse, KanbanColumnResponse

router = APIRouter(tags=["kanban"])


def _board_response(board: KanbanBoard) -> KanbanBoardResponse:
    return KanbanBoardResponse(
        id=board.id,
        project_id=board.project_id,
        name=board.name,
        columns=[
            KanbanColumnResponse(
                id=column.id,
                board_id=column.board_id,
                name=column.name,
                order_index=column.order_index,
                maps_to_status=column.maps_to_status,
            )
            for column in board.columns
        ],
    )


@router.get("/projects/{project_id}/kanban", response_model=KanbanBoardResponse)
async def get_project_kanban_board(
    project_id: UUID,
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    kanban_repo: Annotated[KanbanRepository, Depends(get_kanban_repository)],
) -> KanbanBoardResponse:
    if await project_repo.get(project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    board = await kanban_repo.get_for_project(project_id)
    if board is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kanban board not found")
    return _board_response(board)
