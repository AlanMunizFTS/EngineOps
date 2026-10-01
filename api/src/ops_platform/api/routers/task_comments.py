from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.api.deps import (
    get_audit_recorder,
    get_current_user,
    get_task_comment_repository,
    get_task_repository,
)
from ops_platform.db.session import get_db_session
from ops_platform.domain.entities import TaskComment, User
from ops_platform.domain.ports.audit_recorder import AuditRecorder
from ops_platform.domain.ports.task_comment_repository import TaskCommentRepository
from ops_platform.domain.ports.task_repository import TaskRepository
from ops_platform.schemas.tasks import (
    TaskCommentCreateRequest,
    TaskCommentResponse,
    TaskCommentUpdateRequest,
)

router = APIRouter(tags=["task-comments"])


def _response(comment: TaskComment) -> TaskCommentResponse:
    return TaskCommentResponse(
        id=comment.id,
        task_id=comment.task_id,
        author_id=comment.author_id,
        body=comment.body,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.post("/tasks/{task_id}/comments", response_model=TaskCommentResponse, status_code=201)
async def create_comment(
    task_id: UUID,
    payload: TaskCommentCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
    comments: Annotated[TaskCommentRepository, Depends(get_task_comment_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaskCommentResponse:
    task = await tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    comment = await comments.create(task_id, current_user.id, payload.body)
    await audit.record(
        project_id=task.project_id,
        actor_id=current_user.id,
        entity_type="task_comment",
        entity_id=comment.id,
        action="task.comment_added",
        diff={"task_id": str(task_id)},
    )
    await session.commit()
    return _response(comment)


@router.get("/tasks/{task_id}/comments", response_model=list[TaskCommentResponse])
async def list_comments(
    task_id: UUID,
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
    comments: Annotated[TaskCommentRepository, Depends(get_task_comment_repository)],
) -> list[TaskCommentResponse]:
    if await tasks.get(task_id) is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return [_response(comment) for comment in await comments.list_for_task(task_id)]


@router.patch("/task-comments/{comment_id}", response_model=TaskCommentResponse)
async def update_comment(
    comment_id: UUID,
    payload: TaskCommentUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
    comments: Annotated[TaskCommentRepository, Depends(get_task_comment_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaskCommentResponse:
    comment = await comments.get(comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    task = await tasks.get(comment.task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    updated = await comments.update_body(comment_id, payload.body)
    await audit.record(
        project_id=task.project_id,
        actor_id=current_user.id,
        entity_type="task_comment",
        entity_id=comment_id,
        action="task.comment_edited",
        diff={"task_id": str(task.id)},
    )
    await session.commit()
    return _response(updated)
