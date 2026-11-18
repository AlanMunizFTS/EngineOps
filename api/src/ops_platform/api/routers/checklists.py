from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.api.deps import (
    get_checklist_repository,
    get_current_user,
    get_project_repository,
    get_task_repository,
)
from ops_platform.db.session import get_db_session
from ops_platform.domain.entities import ProjectChecklist, TaskChecklist, User
from ops_platform.domain.ports.checklist_repository import ChecklistRepository
from ops_platform.domain.ports.project_repository import ProjectRepository
from ops_platform.domain.ports.task_repository import TaskRepository
from ops_platform.schemas.checklists import (
    ChecklistCreateRequest,
    ChecklistItemCompletionRequest,
    ChecklistItemCreateRequest,
    ChecklistItemResponse,
    ChecklistItemUpdateRequest,
    ChecklistUpdateRequest,
    ProjectChecklistResponse,
    TaskChecklistItemResponse,
    TaskChecklistResponse,
)

router = APIRouter(tags=["checklists"])


def _project_response(checklist: ProjectChecklist) -> ProjectChecklistResponse:
    return ProjectChecklistResponse(
        id=checklist.id,
        project_id=checklist.project_id,
        name=checklist.name,
        items=[
            ChecklistItemResponse(
                id=item.id,
                checklist_id=item.checklist_id,
                content=item.content,
                position=item.position,
            )
            for item in checklist.items
        ],
    )


def _task_response(checklist: TaskChecklist) -> TaskChecklistResponse:
    return TaskChecklistResponse(
        id=checklist.id,
        project_id=checklist.project_id,
        name=checklist.name,
        items=[
            TaskChecklistItemResponse(
                id=item.id,
                checklist_id=item.checklist_id,
                content=item.content,
                position=item.position,
                completed=item.completed,
            )
            for item in checklist.items
        ],
    )


async def _project_or_404(projects: ProjectRepository, project_id: UUID) -> None:
    if await projects.get(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")


@router.get("/projects/{project_id}/checklists", response_model=list[ProjectChecklistResponse])
async def list_project_checklists(
    project_id: UUID,
    projects: Annotated[ProjectRepository, Depends(get_project_repository)],
    checklists: Annotated[ChecklistRepository, Depends(get_checklist_repository)],
) -> list[ProjectChecklistResponse]:
    await _project_or_404(projects, project_id)
    return [_project_response(item) for item in await checklists.list_for_project(project_id)]


@router.post(
    "/projects/{project_id}/checklists",
    response_model=ProjectChecklistResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project_checklist(
    project_id: UUID,
    payload: ChecklistCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    projects: Annotated[ProjectRepository, Depends(get_project_repository)],
    checklists: Annotated[ChecklistRepository, Depends(get_checklist_repository)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProjectChecklistResponse:
    del current_user
    await _project_or_404(projects, project_id)
    result = await checklists.create(project_id, payload.name.strip())
    await session.commit()
    return _project_response(result)


@router.patch("/checklists/{checklist_id}", response_model=ProjectChecklistResponse)
async def rename_checklist(
    checklist_id: UUID,
    payload: ChecklistUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    checklists: Annotated[ChecklistRepository, Depends(get_checklist_repository)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProjectChecklistResponse:
    del current_user
    if await checklists.get(checklist_id) is None:
        raise HTTPException(status_code=404, detail="Checklist not found")
    result = await checklists.update_name(checklist_id, payload.name.strip())
    await session.commit()
    return _project_response(result)


@router.delete("/checklists/{checklist_id}", status_code=204)
async def delete_checklist(
    checklist_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    checklists: Annotated[ChecklistRepository, Depends(get_checklist_repository)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    del current_user
    if await checklists.get(checklist_id) is None:
        raise HTTPException(status_code=404, detail="Checklist not found")
    await checklists.delete(checklist_id)
    await session.commit()


@router.post(
    "/checklists/{checklist_id}/items",
    response_model=ChecklistItemResponse,
    status_code=201,
)
async def add_checklist_item(
    checklist_id: UUID,
    payload: ChecklistItemCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    checklists: Annotated[ChecklistRepository, Depends(get_checklist_repository)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ChecklistItemResponse:
    del current_user
    if await checklists.get(checklist_id) is None:
        raise HTTPException(status_code=404, detail="Checklist not found")
    item = await checklists.add_item(checklist_id, payload.content.strip())
    await session.commit()
    return ChecklistItemResponse(
        id=item.id,
        checklist_id=item.checklist_id,
        content=item.content,
        position=item.position,
    )


@router.patch("/checklist-items/{item_id}", response_model=ChecklistItemResponse)
async def update_checklist_item(
    item_id: UUID,
    payload: ChecklistItemUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    checklists: Annotated[ChecklistRepository, Depends(get_checklist_repository)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ChecklistItemResponse:
    del current_user
    try:
        item = await checklists.update_item(item_id, payload.content.strip())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await session.commit()
    return ChecklistItemResponse(
        id=item.id,
        checklist_id=item.checklist_id,
        content=item.content,
        position=item.position,
    )


@router.delete("/checklist-items/{item_id}", status_code=204)
async def delete_checklist_item(
    item_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    checklists: Annotated[ChecklistRepository, Depends(get_checklist_repository)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    del current_user
    await checklists.delete_item(item_id)
    await session.commit()


@router.get("/tasks/{task_id}/checklists", response_model=list[TaskChecklistResponse])
async def list_task_checklists(
    task_id: UUID,
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
    checklists: Annotated[ChecklistRepository, Depends(get_checklist_repository)],
) -> list[TaskChecklistResponse]:
    if await tasks.get(task_id) is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return [_task_response(item) for item in await checklists.list_for_task(task_id)]


@router.post("/tasks/{task_id}/checklists/{checklist_id}", response_model=TaskChecklistResponse)
async def attach_checklist(
    task_id: UUID,
    checklist_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
    checklists: Annotated[ChecklistRepository, Depends(get_checklist_repository)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaskChecklistResponse:
    del current_user
    task = await tasks.get(task_id)
    checklist = await checklists.get(checklist_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if checklist is None:
        raise HTTPException(status_code=404, detail="Checklist not found")
    if checklist.project_id != task.project_id:
        raise HTTPException(status_code=422, detail="Checklist belongs to another project")
    result = await checklists.attach_to_task(task_id, checklist_id)
    await session.commit()
    return _task_response(result)


@router.delete("/tasks/{task_id}/checklists/{checklist_id}", status_code=204)
async def detach_checklist(
    task_id: UUID,
    checklist_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    checklists: Annotated[ChecklistRepository, Depends(get_checklist_repository)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    del current_user
    await checklists.detach_from_task(task_id, checklist_id)
    await session.commit()


@router.patch("/tasks/{task_id}/checklist-items/{item_id}", response_model=TaskChecklistResponse)
async def set_checklist_item_completed(
    task_id: UUID,
    item_id: UUID,
    payload: ChecklistItemCompletionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    checklists: Annotated[ChecklistRepository, Depends(get_checklist_repository)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaskChecklistResponse:
    del current_user
    attached = await checklists.list_for_task(task_id)
    if not any(item.id == item_id for checklist in attached for item in checklist.items):
        raise HTTPException(status_code=404, detail="Checklist item is not attached to this task")
    result = await checklists.set_item_completed(task_id, item_id, payload.completed)
    await session.commit()
    return _task_response(result)
