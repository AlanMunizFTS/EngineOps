from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.api.deps import (
    get_area_repository,
    get_audit_log_repository,
    get_audit_recorder,
    get_current_user,
    get_project_repository,
)
from ops_platform.db.session import get_db_session
from ops_platform.domain.entities import (
    AuditLogEntry,
    Project,
    ProjectArea,
    ProjectMember,
    ProjectRole,
    User,
)
from ops_platform.domain.ports.area_repository import AreaRepository
from ops_platform.domain.ports.audit_log_repository import AuditLogRepository
from ops_platform.domain.ports.audit_recorder import AuditRecorder
from ops_platform.domain.ports.project_repository import ProjectRepository
from ops_platform.schemas.audit import AuditLogEntryResponse
from ops_platform.schemas.projects import (
    AreaStatusResponse,
    AreaTypeResponse,
    ProjectAreaResponse,
    ProjectAreaStatusUpdateRequest,
    ProjectCreateRequest,
    ProjectMemberAddRequest,
    ProjectMemberResponse,
    ProjectResponse,
)

router = APIRouter(prefix="/projects", tags=["projects"])


def _project_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        created_by=project.created_by,
        created_at=project.created_at,
    )


def _member_response(member: ProjectMember) -> ProjectMemberResponse:
    return ProjectMemberResponse(
        project_id=member.project_id,
        user_id=member.user_id,
        project_role=member.project_role,
        added_at=member.added_at,
    )


def _audit_response(entry: AuditLogEntry) -> AuditLogEntryResponse:
    return AuditLogEntryResponse(
        id=entry.id,
        project_id=entry.project_id,
        actor_id=entry.actor_id,
        entity_type=entry.entity_type,
        entity_id=entry.entity_id,
        action=entry.action,
        diff=entry.diff,
        occurred_at=entry.occurred_at,
    )


async def _get_project_or_404(project_repo: ProjectRepository, project_id: UUID) -> Project:
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    area_repo: Annotated[AreaRepository, Depends(get_area_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProjectResponse:
    project = await project_repo.create(
        name=payload.name, description=payload.description, created_by=current_user.id
    )
    await project_repo.add_member(project.id, current_user.id, ProjectRole.OWNER)
    await area_repo.create_default_areas(project.id)
    await audit.record(
        project_id=project.id,
        actor_id=current_user.id,
        entity_type="project",
        entity_id=project.id,
        action="project.created",
        diff={"name": project.name},
    )
    await session.commit()
    return _project_response(project)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
) -> list[ProjectResponse]:
    projects = await project_repo.list_all()
    return [_project_response(project) for project in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
) -> ProjectResponse:
    project = await _get_project_or_404(project_repo, project_id)
    return _project_response(project)


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_project_member(
    project_id: UUID,
    payload: ProjectMemberAddRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProjectMemberResponse:
    await _get_project_or_404(project_repo, project_id)
    member = await project_repo.add_member(project_id, payload.user_id, payload.project_role)
    await audit.record(
        project_id=project_id,
        actor_id=current_user.id,
        entity_type="project_member",
        entity_id=payload.user_id,
        action="member.added",
        diff={"project_role": payload.project_role.value},
    )
    await session.commit()
    return _member_response(member)


@router.get("/{project_id}/members", response_model=list[ProjectMemberResponse])
async def list_project_members(
    project_id: UUID,
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
) -> list[ProjectMemberResponse]:
    await _get_project_or_404(project_repo, project_id)
    members = await project_repo.list_members(project_id)
    return [_member_response(member) for member in members]


def _area_response(area: ProjectArea) -> ProjectAreaResponse:
    return ProjectAreaResponse(
        id=area.id,
        project_id=area.project_id,
        area_type=AreaTypeResponse(
            id=area.area_type.id, name=area.area_type.name, description=area.area_type.description
        ),
        status=AreaStatusResponse(
            id=area.status.id,
            area_type_id=area.status.area_type_id,
            name=area.status.name,
            sort_order=area.status.sort_order,
        ),
        updated_by=area.updated_by,
        updated_at=area.updated_at,
    )


@router.get("/{project_id}/areas", response_model=list[ProjectAreaResponse])
async def list_project_areas(
    project_id: UUID,
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    area_repo: Annotated[AreaRepository, Depends(get_area_repository)],
) -> list[ProjectAreaResponse]:
    await _get_project_or_404(project_repo, project_id)
    areas = await area_repo.list_for_project(project_id)
    return [_area_response(area) for area in areas]


@router.patch("/{project_id}/areas/{area_id}", response_model=ProjectAreaResponse)
async def update_project_area_status(
    project_id: UUID,
    area_id: UUID,
    payload: ProjectAreaStatusUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    area_repo: Annotated[AreaRepository, Depends(get_area_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProjectAreaResponse:
    await _get_project_or_404(project_repo, project_id)

    existing = {area.id: area for area in await area_repo.list_for_project(project_id)}
    current_area = existing.get(area_id)
    if current_area is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")

    try:
        updated = await area_repo.update_status(area_id, payload.status_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    await audit.record(
        project_id=project_id,
        actor_id=current_user.id,
        entity_type="project_area",
        entity_id=area_id,
        action="area.status_changed",
        diff={
            "area_type": updated.area_type.name,
            "from": current_area.status.name,
            "to": updated.status.name,
        },
    )
    await session.commit()
    return _area_response(updated)


@router.get("/{project_id}/timeline", response_model=list[AuditLogEntryResponse])
async def get_project_timeline(
    project_id: UUID,
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    audit_log_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> list[AuditLogEntryResponse]:
    await _get_project_or_404(project_repo, project_id)
    entries = await audit_log_repo.list_for_project(project_id)
    return [_audit_response(entry) for entry in entries]
