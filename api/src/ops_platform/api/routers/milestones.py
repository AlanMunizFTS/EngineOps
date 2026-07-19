from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.api.deps import (
    get_audit_recorder,
    get_current_user,
    get_issue_repository,
    get_milestone_repository,
    get_project_repository,
)
from ops_platform.db.session import get_db_session
from ops_platform.domain.entities import IssueStatus, Milestone, User
from ops_platform.domain.ports.audit_recorder import AuditRecorder
from ops_platform.domain.ports.issue_repository import IssueRepository
from ops_platform.domain.ports.milestone_repository import MilestoneRepository
from ops_platform.domain.ports.project_repository import ProjectRepository
from ops_platform.schemas.milestones import (
    MilestoneCreateRequest,
    MilestoneProgressResponse,
    MilestoneResponse,
    MilestoneStatusUpdateRequest,
)

router = APIRouter(tags=["milestones"])


def _milestone_response(milestone: Milestone) -> MilestoneResponse:
    return MilestoneResponse(
        id=milestone.id,
        project_id=milestone.project_id,
        title=milestone.title,
        description=milestone.description,
        due_date=milestone.due_date,
        status=milestone.status,
        created_at=milestone.created_at,
    )


async def _get_project_or_404(project_repo: ProjectRepository, project_id: UUID) -> None:
    if await project_repo.get(project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


async def _get_milestone_or_404(
    milestone_repo: MilestoneRepository, milestone_id: UUID
) -> Milestone:
    milestone = await milestone_repo.get(milestone_id)
    if milestone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")
    return milestone


@router.post(
    "/projects/{project_id}/milestones",
    response_model=MilestoneResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_milestone(
    project_id: UUID,
    payload: MilestoneCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    milestone_repo: Annotated[MilestoneRepository, Depends(get_milestone_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MilestoneResponse:
    await _get_project_or_404(project_repo, project_id)

    milestone = await milestone_repo.create(
        project_id=project_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
    )
    await audit.record(
        project_id=project_id,
        actor_id=current_user.id,
        entity_type="milestone",
        entity_id=milestone.id,
        action="milestone.created",
        diff={"title": milestone.title},
    )
    await session.commit()
    return _milestone_response(milestone)


@router.get("/projects/{project_id}/milestones", response_model=list[MilestoneProgressResponse])
async def list_project_milestones(
    project_id: UUID,
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    milestone_repo: Annotated[MilestoneRepository, Depends(get_milestone_repository)],
    issue_repo: Annotated[IssueRepository, Depends(get_issue_repository)],
) -> list[MilestoneProgressResponse]:
    await _get_project_or_404(project_repo, project_id)

    milestones = await milestone_repo.list_for_project(project_id)
    responses = []
    for milestone in milestones:
        issues = await issue_repo.list_for_project(project_id, milestone_id=milestone.id)
        closed = sum(1 for issue in issues if issue.status == IssueStatus.DONE)
        total = len(issues)
        responses.append(
            MilestoneProgressResponse(
                **_milestone_response(milestone).model_dump(),
                total_issues=total,
                closed_issues=closed,
                percent_complete=round(closed / total * 100, 1) if total else 0.0,
            )
        )
    return responses


@router.patch("/milestones/{milestone_id}/status", response_model=MilestoneResponse)
async def update_milestone_status(
    milestone_id: UUID,
    payload: MilestoneStatusUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    milestone_repo: Annotated[MilestoneRepository, Depends(get_milestone_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MilestoneResponse:
    milestone = await _get_milestone_or_404(milestone_repo, milestone_id)
    updated = await milestone_repo.update_status(milestone_id, payload.status)
    await audit.record(
        project_id=milestone.project_id,
        actor_id=current_user.id,
        entity_type="milestone",
        entity_id=milestone_id,
        action="milestone.status_changed",
        diff={"from": milestone.status.value, "to": updated.status.value},
    )
    await session.commit()
    return _milestone_response(updated)
