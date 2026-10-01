from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.api.deps import (
    get_audit_recorder,
    get_current_user,
    get_milestone_repository,
    get_project_repository,
)
from ops_platform.application.errors import NotFoundError
from ops_platform.application.milestone_service import MilestoneService
from ops_platform.db.session import get_db_session
from ops_platform.domain.entities import Milestone, User
from ops_platform.domain.ports.audit_recorder import AuditRecorder
from ops_platform.domain.ports.milestone_repository import MilestoneRepository
from ops_platform.domain.ports.project_repository import ProjectRepository
from ops_platform.schemas.milestones import (
    MilestoneCreateRequest,
    MilestoneResponse,
    MilestoneUpdateRequest,
)

router = APIRouter(tags=["milestones"])


def _response(value: Milestone) -> MilestoneResponse:
    return MilestoneResponse(
        id=value.id,
        project_id=value.project_id,
        title=value.title,
        description=value.description,
        status=value.status,
        due_date=value.due_date,
        created_at=value.created_at,
        updated_at=value.updated_at,
        total_tasks=value.total_tasks,
        completed_tasks=value.completed_tasks,
        progress_percentage=value.progress_percentage,
    )


@router.post(
    "/projects/{project_id}/milestones", response_model=MilestoneResponse, status_code=201
)
async def create_milestone(
    project_id: UUID,
    payload: MilestoneCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    projects: Annotated[ProjectRepository, Depends(get_project_repository)],
    milestones: Annotated[MilestoneRepository, Depends(get_milestone_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MilestoneResponse:
    if await projects.get(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    value = await MilestoneService(milestones).create(
        project_id=project_id, **payload.model_dump()
    )
    await audit.record(
        project_id=project_id,
        actor_id=current_user.id,
        entity_type="milestone",
        entity_id=value.id,
        action="milestone.created",
        diff={"title": value.title},
    )
    await session.commit()
    return _response(value)


@router.get("/projects/{project_id}/milestones", response_model=list[MilestoneResponse])
async def list_milestones(
    project_id: UUID,
    projects: Annotated[ProjectRepository, Depends(get_project_repository)],
    milestones: Annotated[MilestoneRepository, Depends(get_milestone_repository)],
) -> list[MilestoneResponse]:
    if await projects.get(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return [_response(value) for value in await milestones.list_for_project(project_id)]


@router.get("/milestones/{milestone_id}", response_model=MilestoneResponse)
async def get_milestone(
    milestone_id: UUID,
    milestones: Annotated[MilestoneRepository, Depends(get_milestone_repository)],
) -> MilestoneResponse:
    try:
        return _response(await MilestoneService(milestones).get(milestone_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/milestones/{milestone_id}", response_model=MilestoneResponse)
async def update_milestone(
    milestone_id: UUID,
    payload: MilestoneUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    milestones: Annotated[MilestoneRepository, Depends(get_milestone_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MilestoneResponse:
    service = MilestoneService(milestones)
    try:
        before = await service.get(milestone_id)
        changes = payload.model_dump(exclude_unset=True)
        if changes.get("title", ...) is None:
            raise HTTPException(status_code=422, detail="title cannot be null")
        updated = await service.update(milestone_id, **changes)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await audit.record(
        project_id=before.project_id,
        actor_id=current_user.id,
        entity_type="milestone",
        entity_id=milestone_id,
        action="milestone.updated",
        diff=changes,
    )
    await session.commit()
    return _response(updated)


@router.delete("/milestones/{milestone_id}", status_code=204)
async def delete_milestone(
    milestone_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    milestones: Annotated[MilestoneRepository, Depends(get_milestone_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    try:
        deleted = await MilestoneService(milestones).delete(milestone_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await audit.record(
        project_id=deleted.project_id,
        actor_id=current_user.id,
        entity_type="milestone",
        entity_id=milestone_id,
        action="milestone.deleted",
        diff={"title": deleted.title},
    )
    await session.commit()
