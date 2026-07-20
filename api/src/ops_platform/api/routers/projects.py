from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.api.deps import (
    get_audit_log_repository,
    get_audit_recorder,
    get_current_user,
    get_kanban_repository,
    get_project_repository,
)
from ops_platform.db.session import get_db_session
from ops_platform.domain.entities import (
    AuditLogEntry,
    Project,
    ProjectMember,
    ProjectMemberDetail,
    ProjectRole,
    User,
)
from ops_platform.domain.ports.audit_log_repository import AuditLogRepository
from ops_platform.domain.ports.audit_recorder import AuditRecorder
from ops_platform.domain.ports.kanban_repository import KanbanRepository
from ops_platform.domain.ports.project_repository import ProjectRepository
from ops_platform.schemas.audit import AuditLogEntryResponse
from ops_platform.schemas.projects import (
    ProjectCreateRequest,
    ProjectMemberAddRequest,
    ProjectMemberDetailResponse,
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


def _member_detail_response(detail: ProjectMemberDetail) -> ProjectMemberDetailResponse:
    return ProjectMemberDetailResponse(
        project_id=detail.member.project_id,
        user_id=detail.member.user_id,
        project_role=detail.member.project_role,
        added_at=detail.member.added_at,
        email=detail.email,
        full_name=detail.full_name,
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
    kanban_repo: Annotated[KanbanRepository, Depends(get_kanban_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProjectResponse:
    project = await project_repo.create(
        name=payload.name, description=payload.description, created_by=current_user.id
    )
    await project_repo.add_member(project.id, current_user.id, ProjectRole.OWNER)
    await kanban_repo.create_default_board(project.id)
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


@router.get("/{project_id}/members", response_model=list[ProjectMemberDetailResponse])
async def list_project_members(
    project_id: UUID,
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
) -> list[ProjectMemberDetailResponse]:
    await _get_project_or_404(project_repo, project_id)
    members = await project_repo.list_members_with_users(project_id)
    return [_member_detail_response(detail) for detail in members]


@router.get("/{project_id}/timeline", response_model=list[AuditLogEntryResponse])
async def get_project_timeline(
    project_id: UUID,
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    audit_log_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> list[AuditLogEntryResponse]:
    await _get_project_or_404(project_repo, project_id)
    entries = await audit_log_repo.list_for_project(project_id)
    return [_audit_response(entry) for entry in entries]
