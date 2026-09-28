from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.api.deps import (
    get_audit_recorder,
    get_current_user,
    get_kanban_repository,
    get_project_repository,
)
from ops_platform.db.session import get_db_session
from ops_platform.domain.entities import KanbanBoard, KanbanColumn, User
from ops_platform.domain.ports.audit_recorder import AuditRecorder
from ops_platform.domain.ports.kanban_repository import KanbanRepository
from ops_platform.domain.ports.project_repository import ProjectRepository
from ops_platform.schemas.kanban import (
    KanbanBoardCreateRequest,
    KanbanBoardRenameRequest,
    KanbanBoardResponse,
    KanbanColumnCreateRequest,
    KanbanColumnReorderRequest,
    KanbanColumnResponse,
    KanbanColumnUpdateRequest,
)

router = APIRouter(tags=["kanban"])


def _column_response(column: KanbanColumn) -> KanbanColumnResponse:
    return KanbanColumnResponse(
        id=column.id,
        board_id=column.board_id,
        name=column.name,
        order_index=column.order_index,
        maps_to_statuses=column.maps_to_statuses,
    )


def _board_response(board: KanbanBoard) -> KanbanBoardResponse:
    return KanbanBoardResponse(
        id=board.id,
        project_id=board.project_id,
        name=board.name,
        columns=[_column_response(column) for column in board.columns],
    )


async def _get_project_or_404(project_repo: ProjectRepository, project_id: UUID) -> None:
    if await project_repo.get(project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


async def _get_board_or_404(kanban_repo: KanbanRepository, board_id: UUID) -> KanbanBoard:
    board = await kanban_repo.get(board_id)
    if board is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kanban board not found")
    return board


async def _get_column_and_board_or_404(
    kanban_repo: KanbanRepository, column_id: UUID
) -> tuple[KanbanColumn, KanbanBoard]:
    column = await kanban_repo.get_column(column_id)
    if column is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Column not found")
    board = await _get_board_or_404(kanban_repo, column.board_id)
    return column, board


@router.post(
    "/projects/{project_id}/kanban-boards",
    response_model=KanbanBoardResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_kanban_board(
    project_id: UUID,
    payload: KanbanBoardCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    kanban_repo: Annotated[KanbanRepository, Depends(get_kanban_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KanbanBoardResponse:
    await _get_project_or_404(project_repo, project_id)
    board = await kanban_repo.create_board(project_id, payload.name)
    await audit.record(
        project_id=project_id,
        actor_id=current_user.id,
        entity_type="kanban_board",
        entity_id=board.id,
        action="kanban_board.created",
        diff={"name": board.name},
    )
    await session.commit()
    return _board_response(board)


@router.get("/projects/{project_id}/kanban-boards", response_model=list[KanbanBoardResponse])
async def list_kanban_boards(
    project_id: UUID,
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    kanban_repo: Annotated[KanbanRepository, Depends(get_kanban_repository)],
) -> list[KanbanBoardResponse]:
    await _get_project_or_404(project_repo, project_id)
    boards = await kanban_repo.list_for_project(project_id)
    return [_board_response(board) for board in boards]


@router.get("/kanban-boards/{board_id}", response_model=KanbanBoardResponse)
async def get_kanban_board(
    board_id: UUID,
    kanban_repo: Annotated[KanbanRepository, Depends(get_kanban_repository)],
) -> KanbanBoardResponse:
    board = await _get_board_or_404(kanban_repo, board_id)
    return _board_response(board)


@router.patch("/kanban-boards/{board_id}", response_model=KanbanBoardResponse)
async def rename_kanban_board(
    board_id: UUID,
    payload: KanbanBoardRenameRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    kanban_repo: Annotated[KanbanRepository, Depends(get_kanban_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KanbanBoardResponse:
    board = await _get_board_or_404(kanban_repo, board_id)
    updated = await kanban_repo.rename_board(board_id, payload.name)
    await audit.record(
        project_id=board.project_id,
        actor_id=current_user.id,
        entity_type="kanban_board",
        entity_id=board_id,
        action="kanban_board.renamed",
        diff={"from": board.name, "to": updated.name},
    )
    await session.commit()
    return _board_response(updated)


@router.delete("/kanban-boards/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_kanban_board(
    board_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    kanban_repo: Annotated[KanbanRepository, Depends(get_kanban_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    board = await _get_board_or_404(kanban_repo, board_id)
    await kanban_repo.delete_board(board_id)
    await audit.record(
        project_id=board.project_id,
        actor_id=current_user.id,
        entity_type="kanban_board",
        entity_id=board_id,
        action="kanban_board.deleted",
        diff={"name": board.name},
    )
    await session.commit()


@router.post(
    "/kanban-boards/{board_id}/columns",
    response_model=KanbanColumnResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_kanban_column(
    board_id: UUID,
    payload: KanbanColumnCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    kanban_repo: Annotated[KanbanRepository, Depends(get_kanban_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KanbanColumnResponse:
    board = await _get_board_or_404(kanban_repo, board_id)
    column = await kanban_repo.create_column(board_id, payload.name, payload.maps_to_statuses)
    await audit.record(
        project_id=board.project_id,
        actor_id=current_user.id,
        entity_type="kanban_column",
        entity_id=column.id,
        action="kanban_column.created",
        diff={"name": column.name, "maps_to_statuses": [s.value for s in column.maps_to_statuses]},
    )
    await session.commit()
    return _column_response(column)


@router.patch("/kanban-boards/{board_id}/columns/reorder", response_model=KanbanBoardResponse)
async def reorder_kanban_columns(
    board_id: UUID,
    payload: KanbanColumnReorderRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    kanban_repo: Annotated[KanbanRepository, Depends(get_kanban_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KanbanBoardResponse:
    board = await _get_board_or_404(kanban_repo, board_id)
    existing_ids = {column.id for column in board.columns}
    if set(payload.ordered_column_ids) != existing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ordered_column_ids must include every column of this board exactly once",
        )
    try:
        updated = await kanban_repo.reorder_columns(board_id, payload.ordered_column_ids)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await audit.record(
        project_id=board.project_id,
        actor_id=current_user.id,
        entity_type="kanban_board",
        entity_id=board_id,
        action="kanban_column.reordered",
        diff={"ordered_column_ids": [str(c) for c in payload.ordered_column_ids]},
    )
    await session.commit()
    return _board_response(updated)


@router.patch("/kanban-columns/{column_id}", response_model=KanbanColumnResponse)
async def update_kanban_column(
    column_id: UUID,
    payload: KanbanColumnUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    kanban_repo: Annotated[KanbanRepository, Depends(get_kanban_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KanbanColumnResponse:
    _, board = await _get_column_and_board_or_404(kanban_repo, column_id)
    updated = await kanban_repo.update_column(column_id, payload.name, payload.maps_to_statuses)
    await audit.record(
        project_id=board.project_id,
        actor_id=current_user.id,
        entity_type="kanban_column",
        entity_id=column_id,
        action="kanban_column.updated",
        diff={
            "name": updated.name,
            "maps_to_statuses": [s.value for s in updated.maps_to_statuses],
        },
    )
    await session.commit()
    return _column_response(updated)


@router.delete("/kanban-columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_kanban_column(
    column_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    kanban_repo: Annotated[KanbanRepository, Depends(get_kanban_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    column, board = await _get_column_and_board_or_404(kanban_repo, column_id)
    await kanban_repo.delete_column(column_id)
    await audit.record(
        project_id=board.project_id,
        actor_id=current_user.id,
        entity_type="kanban_column",
        entity_id=column_id,
        action="kanban_column.deleted",
        diff={"name": column.name},
    )
    await session.commit()
