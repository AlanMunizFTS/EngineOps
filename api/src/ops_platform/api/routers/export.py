import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from ops_platform.adapters.xlsx.workbook import build_project_export_workbook
from ops_platform.api.deps import (
    get_kanban_repository,
    get_project_repository,
    get_task_repository,
)
from ops_platform.domain.ports.kanban_repository import KanbanRepository
from ops_platform.domain.ports.project_repository import ProjectRepository
from ops_platform.domain.ports.task_repository import TaskRepository

router = APIRouter(tags=["export"])

_XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9_-]+")


@router.get("/projects/{project_id}/export.xlsx")
async def export_project_workbook(
    project_id: UUID,
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    task_repo: Annotated[TaskRepository, Depends(get_task_repository)],
    kanban_repo: Annotated[KanbanRepository, Depends(get_kanban_repository)],
) -> Response:
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    tasks = await task_repo.list_for_project(project_id, include_subtasks=True)
    boards = await kanban_repo.list_for_project(project_id)
    board = boards[0] if boards else None
    members = await project_repo.list_members_with_users(project_id)
    member_names = {detail.member.user_id: detail.full_name for detail in members}

    content = build_project_export_workbook(project, tasks, board, member_names)
    filename = _UNSAFE_FILENAME_CHARS.sub("_", project.name).strip("_") or "project"
    return Response(
        content=content,
        media_type=_XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}_export.xlsx"'},
    )
