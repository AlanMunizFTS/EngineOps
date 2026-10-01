from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.api.deps import (
    get_audit_log_repository,
    get_audit_recorder,
    get_current_user,
    get_label_repository,
    get_milestone_repository,
    get_project_repository,
    get_task_repository,
)
from ops_platform.application.errors import ConflictError, NotFoundError, ValidationError
from ops_platform.application.task_service import TaskService
from ops_platform.db.session import get_db_session
from ops_platform.domain.entities import Task, TaskPriority, TaskStatus, TaskType, User
from ops_platform.domain.ports.audit_log_repository import AuditLogRepository
from ops_platform.domain.ports.audit_recorder import AuditRecorder
from ops_platform.domain.ports.label_repository import LabelRepository
from ops_platform.domain.ports.milestone_repository import MilestoneRepository
from ops_platform.domain.ports.project_repository import ProjectRepository
from ops_platform.domain.ports.task_repository import TaskRepository
from ops_platform.domain.scheduling import (
    ScheduleStatus,
    calculate_days_planned,
    calculate_priority_score,
    calculate_schedule_status,
    calculate_urgency,
    should_auto_advance_to_todo,
    to_business_date,
    today_in_business_timezone,
    working_days_taken,
)
from ops_platform.schemas.audit import AuditLogEntryResponse
from ops_platform.schemas.labels import LabelResponse
from ops_platform.schemas.tasks import (
    TaskCreateRequest,
    TaskParentUpdateRequest,
    TaskResponse,
    TaskStatusUpdateRequest,
    TaskUpdateRequest,
)

router = APIRouter(tags=["tasks"])


def _service(
    tasks: TaskRepository, milestones: MilestoneRepository, labels: LabelRepository
) -> TaskService:
    return TaskService(tasks, milestones, labels)


def _raise_http(exc: Exception) -> None:
    if isinstance(exc, NotFoundError):
        code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ConflictError):
        code = status.HTTP_409_CONFLICT
    else:
        code = status.HTTP_422_UNPROCESSABLE_ENTITY
    raise HTTPException(status_code=code, detail=str(exc)) from exc


def task_response(task: Task) -> TaskResponse:
    today = today_in_business_timezone()
    urgency = calculate_urgency(today, task.due_date)
    closed_at_date = to_business_date(task.closed_at) if task.closed_at else None
    schedule_status = calculate_schedule_status(today, task.due_date, closed_at_date)
    return TaskResponse(
        id=task.id,
        project_id=task.project_id,
        milestone_id=task.milestone_id,
        parent_task_id=task.parent_task_id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        task_type=task.task_type,
        assignee_id=task.assignee_id,
        created_by=task.created_by,
        created_at=task.created_at,
        updated_at=task.updated_at,
        closed_at=task.closed_at,
        closed_at_date=closed_at_date,
        parent_assigned_at=task.parent_assigned_at,
        start_date=task.start_date,
        due_date=task.due_date,
        days_planned=calculate_days_planned(task.start_date, task.due_date),
        days_taken=(
            working_days_taken(task.start_date, closed_at_date or today)
            if task.start_date is not None
            else None
        ),
        urgency=urgency,
        priority_score=(
            None
            if task.status == TaskStatus.DONE
            else calculate_priority_score(
                urgency,
                task.priority,
                is_overdue=schedule_status == ScheduleStatus.LATE,
                has_started=task.start_date is None or task.start_date <= today,
            )
        ),
        schedule_status=schedule_status,
        subtasks_total=task.subtasks_total,
        subtasks_completed=task.subtasks_completed,
        labels=[
            LabelResponse(
                id=label.id,
                project_id=label.project_id,
                name=label.name,
                color=label.color,
            )
            for label in task.labels
        ],
    )


async def _project_or_404(projects: ProjectRepository, project_id: UUID) -> None:
    if await projects.get(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")


@router.post("/projects/{project_id}/tasks", response_model=TaskResponse, status_code=201)
async def create_task(
    project_id: UUID,
    payload: TaskCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    projects: Annotated[ProjectRepository, Depends(get_project_repository)],
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
    milestones: Annotated[MilestoneRepository, Depends(get_milestone_repository)],
    labels: Annotated[LabelRepository, Depends(get_label_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaskResponse:
    await _project_or_404(projects, project_id)
    try:
        task = await _service(tasks, milestones, labels).create_task(
            project_id=project_id, created_by=current_user.id, **payload.model_dump()
        )
    except (NotFoundError, ConflictError, ValidationError) as exc:
        _raise_http(exc)
    await audit.record(
        project_id=project_id,
        actor_id=current_user.id,
        entity_type="task",
        entity_id=task.id,
        action="task.created",
        diff={"title": task.title, "task_type": task.task_type.value},
    )
    await session.commit()
    return task_response(task)


@router.get("/projects/{project_id}/tasks", response_model=list[TaskResponse])
async def list_project_tasks(
    project_id: UUID,
    projects: Annotated[ProjectRepository, Depends(get_project_repository)],
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    include_subtasks: bool = False,
    status_filter: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: TaskPriority | None = None,
    task_type: TaskType | None = None,
    assignee_id: UUID | None = None,
    milestone_id: UUID | None = None,
    label_id: UUID | None = None,
) -> list[TaskResponse]:
    await _project_or_404(projects, project_id)
    result = await tasks.list_for_project(
        project_id,
        include_subtasks=include_subtasks,
        status=status_filter,
        priority=priority,
        task_type=task_type,
        assignee_id=assignee_id,
        milestone_id=milestone_id,
        label_id=label_id,
    )
    if status_filter is None:
        today = today_in_business_timezone()
        changed = False
        for index, task in enumerate(result):
            if should_auto_advance_to_todo(today, task.status, task.start_date):
                result[index] = await tasks.set_status(task.id, TaskStatus.TODO)
                changed = True
        if changed:
            await session.commit()
    return [task_response(task) for task in result]


@router.get("/tasks/assigned-to-me", response_model=list[TaskResponse])
async def list_my_tasks(
    current_user: Annotated[User, Depends(get_current_user)],
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
) -> list[TaskResponse]:
    return [task_response(task) for task in await tasks.list_pending_for_assignee(current_user.id)]


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
    milestones: Annotated[MilestoneRepository, Depends(get_milestone_repository)],
    labels: Annotated[LabelRepository, Depends(get_label_repository)],
) -> TaskResponse:
    try:
        return task_response(await _service(tasks, milestones, labels).get(task_id))
    except NotFoundError as exc:
        _raise_http(exc)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    payload: TaskUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
    milestones: Annotated[MilestoneRepository, Depends(get_milestone_repository)],
    labels: Annotated[LabelRepository, Depends(get_label_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaskResponse:
    service = _service(tasks, milestones, labels)
    try:
        before = await service.get(task_id)
        changes: dict[str, Any] = payload.model_dump(exclude_unset=True)
        if changes.get("title", ...) is None:
            raise ValidationError("title cannot be null")
        updated = await service.update_task(task_id, **changes)
    except (NotFoundError, ConflictError, ValidationError) as exc:
        _raise_http(exc)
    role = "subtask" if before.is_subtask else "task"
    await audit.record(
        project_id=before.project_id,
        actor_id=current_user.id,
        entity_type="task",
        entity_id=task_id,
        action=f"{role}.updated",
        diff={
            key: str(value) if isinstance(value, UUID) else value for key, value in changes.items()
        },
    )
    await session.commit()
    return task_response(updated)


@router.patch("/tasks/{task_id}/status", response_model=TaskResponse)
async def change_task_status(
    task_id: UUID,
    payload: TaskStatusUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
    milestones: Annotated[MilestoneRepository, Depends(get_milestone_repository)],
    labels: Annotated[LabelRepository, Depends(get_label_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaskResponse:
    service = _service(tasks, milestones, labels)
    try:
        before = await service.get(task_id)
        updated = await service.change_status(task_id, payload.status)
    except (NotFoundError, ConflictError, ValidationError) as exc:
        _raise_http(exc)
    role = "subtask" if before.is_subtask else "task"
    await audit.record(
        project_id=before.project_id,
        actor_id=current_user.id,
        entity_type="task",
        entity_id=task_id,
        action=f"{role}.status_changed",
        diff={"old_status": before.status.value, "new_status": updated.status.value},
    )
    await session.commit()
    return task_response(updated)


@router.get("/tasks/{task_id}/subtasks", response_model=list[TaskResponse])
async def list_subtasks(
    task_id: UUID,
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
    milestones: Annotated[MilestoneRepository, Depends(get_milestone_repository)],
    labels: Annotated[LabelRepository, Depends(get_label_repository)],
) -> list[TaskResponse]:
    try:
        await _service(tasks, milestones, labels).get(task_id)
    except NotFoundError as exc:
        _raise_http(exc)
    return [task_response(task) for task in await tasks.list_subtasks(task_id)]


@router.post("/tasks/{task_id}/subtasks", response_model=TaskResponse, status_code=201)
async def create_subtask(
    task_id: UUID,
    payload: TaskCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
    milestones: Annotated[MilestoneRepository, Depends(get_milestone_repository)],
    labels: Annotated[LabelRepository, Depends(get_label_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaskResponse:
    service = _service(tasks, milestones, labels)
    try:
        parent = await service.get(task_id)
        if payload.milestone_id is not None:
            raise ConflictError("Subtasks cannot be assigned directly to a Milestone")
        values = payload.model_dump(exclude={"milestone_id"})
        subtask = await service.create_subtask(
            task_id, project_id=parent.project_id, created_by=current_user.id, **values
        )
    except (NotFoundError, ConflictError, ValidationError) as exc:
        _raise_http(exc)
    await audit.record(
        project_id=parent.project_id,
        actor_id=current_user.id,
        entity_type="task",
        entity_id=subtask.id,
        action="subtask.created",
        diff={"title": subtask.title, "parent_task_id": str(task_id)},
    )
    await session.commit()
    return task_response(subtask)


@router.patch("/tasks/{task_id}/parent", response_model=TaskResponse)
async def reparent_task(
    task_id: UUID,
    payload: TaskParentUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
    milestones: Annotated[MilestoneRepository, Depends(get_milestone_repository)],
    labels: Annotated[LabelRepository, Depends(get_label_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaskResponse:
    service = _service(tasks, milestones, labels)
    try:
        before = await service.get(task_id)
        updated = await service.reparent_task(task_id, payload.parent_task_id)
    except (NotFoundError, ConflictError, ValidationError) as exc:
        _raise_http(exc)
    await audit.record(
        project_id=before.project_id,
        actor_id=current_user.id,
        entity_type="task",
        entity_id=task_id,
        action="task.reparented",
        diff={
            "old_parent_task_id": str(before.parent_task_id) if before.parent_task_id else None,
            "new_parent_task_id": str(updated.parent_task_id) if updated.parent_task_id else None,
        },
    )
    await session.commit()
    return task_response(updated)


@router.post("/tasks/{task_id}/labels/{label_id}", response_model=TaskResponse)
async def attach_label(
    task_id: UUID,
    label_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
    milestones: Annotated[MilestoneRepository, Depends(get_milestone_repository)],
    labels: Annotated[LabelRepository, Depends(get_label_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaskResponse:
    service = _service(tasks, milestones, labels)
    try:
        updated = await service.add_label(task_id, label_id)
    except (NotFoundError, ConflictError, ValidationError) as exc:
        _raise_http(exc)
    await audit.record(
        project_id=updated.project_id,
        actor_id=current_user.id,
        entity_type="task",
        entity_id=task_id,
        action="task.label_attached",
        diff={"label_id": str(label_id)},
    )
    await session.commit()
    return task_response(updated)


@router.delete("/tasks/{task_id}/labels/{label_id}", response_model=TaskResponse)
async def detach_label(
    task_id: UUID,
    label_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
    milestones: Annotated[MilestoneRepository, Depends(get_milestone_repository)],
    labels: Annotated[LabelRepository, Depends(get_label_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TaskResponse:
    try:
        updated = await _service(tasks, milestones, labels).remove_label(task_id, label_id)
    except (NotFoundError, ConflictError, ValidationError) as exc:
        _raise_http(exc)
    await audit.record(
        project_id=updated.project_id,
        actor_id=current_user.id,
        entity_type="task",
        entity_id=task_id,
        action="task.label_detached",
        diff={"label_id": str(label_id)},
    )
    await session.commit()
    return task_response(updated)


@router.get("/tasks/{task_id}/history", response_model=list[AuditLogEntryResponse])
async def task_history(
    task_id: UUID,
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
    audit_logs: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> list[AuditLogEntryResponse]:
    if await tasks.get(task_id) is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return [
        AuditLogEntryResponse(
            id=entry.id,
            project_id=entry.project_id,
            actor_id=entry.actor_id,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            action=entry.action,
            diff=entry.diff,
            occurred_at=entry.occurred_at,
        )
        for entry in await audit_logs.list_for_entity("task", task_id)
    ]


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    tasks: Annotated[TaskRepository, Depends(get_task_repository)],
    milestones: Annotated[MilestoneRepository, Depends(get_milestone_repository)],
    labels: Annotated[LabelRepository, Depends(get_label_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    try:
        deleted = await _service(tasks, milestones, labels).delete_task(task_id)
    except (NotFoundError, ConflictError, ValidationError) as exc:
        _raise_http(exc)
    role = "subtask" if deleted.is_subtask else "task"
    await audit.record(
        project_id=deleted.project_id,
        actor_id=current_user.id,
        entity_type="task",
        entity_id=task_id,
        action=f"{role}.deleted",
        diff={"title": deleted.title},
    )
    await session.commit()
