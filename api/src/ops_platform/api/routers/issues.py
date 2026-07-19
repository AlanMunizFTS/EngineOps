from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.api.deps import (
    get_audit_recorder,
    get_current_user,
    get_implementation_repository,
    get_issue_repository,
    get_machine_repository,
    get_plant_repository,
    get_project_repository,
)
from ops_platform.db.session import get_db_session
from ops_platform.domain.entities import Issue, IssueStatus, User
from ops_platform.domain.ports.audit_recorder import AuditRecorder
from ops_platform.domain.ports.implementation_repository import ImplementationRepository
from ops_platform.domain.ports.issue_repository import IssueRepository
from ops_platform.domain.ports.machine_repository import MachineRepository
from ops_platform.domain.ports.plant_repository import PlantRepository
from ops_platform.domain.ports.project_repository import ProjectRepository
from ops_platform.schemas.issues import (
    IssueCreateRequest,
    IssueLabelAttachRequest,
    IssueResponse,
    IssueStatusUpdateRequest,
    IssueUpdateRequest,
)
from ops_platform.schemas.labels import LabelResponse

router = APIRouter(tags=["issues"])


def _issue_response(issue: Issue) -> IssueResponse:
    return IssueResponse(
        id=issue.id,
        project_id=issue.project_id,
        plant_id=issue.plant_id,
        machine_id=issue.machine_id,
        implementation_id=issue.implementation_id,
        title=issue.title,
        description=issue.description,
        status=issue.status,
        priority=issue.priority,
        issue_type=issue.issue_type,
        milestone_id=issue.milestone_id,
        assignee_id=issue.assignee_id,
        created_by=issue.created_by,
        created_at=issue.created_at,
        closed_at=issue.closed_at,
        labels=[
            LabelResponse(
                id=label.id, project_id=label.project_id, name=label.name, color=label.color
            )
            for label in issue.labels
        ],
    )


async def _get_project_or_404(project_repo: ProjectRepository, project_id: UUID) -> None:
    if await project_repo.get(project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


async def _get_issue_or_404(issue_repo: IssueRepository, issue_id: UUID) -> Issue:
    issue = await issue_repo.get(issue_id)
    if issue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return issue


async def _validate_hierarchy_link(
    *,
    project_id: UUID,
    plant_id: UUID | None,
    machine_id: UUID | None,
    implementation_id: UUID | None,
    plant_repo: PlantRepository,
    machine_repo: MachineRepository,
    implementation_repo: ImplementationRepository,
) -> None:
    """Belt-and-suspenders check on top of the DB CHECK constraint: confirms
    whichever hierarchy node is linked actually belongs to this project (the
    CHECK constraint only enforces "at most one field set", not ownership)."""
    not_found = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Link target not found"
    )

    if plant_id is not None:
        plant = await plant_repo.get(plant_id)
        if plant is None or plant.project_id != project_id:
            raise not_found
    if machine_id is not None:
        machine = await machine_repo.get(machine_id)
        plant = await plant_repo.get(machine.plant_id) if machine else None
        if machine is None or plant is None or plant.project_id != project_id:
            raise not_found
    if implementation_id is not None:
        implementation = await implementation_repo.get(implementation_id)
        if implementation is None:
            raise not_found
        machine = await machine_repo.get(implementation.machine_id)
        if machine is None:
            raise not_found
        plant = await plant_repo.get(machine.plant_id)
        if plant is None or plant.project_id != project_id:
            raise not_found


@router.post(
    "/projects/{project_id}/issues",
    response_model=IssueResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_issue(
    project_id: UUID,
    payload: IssueCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    plant_repo: Annotated[PlantRepository, Depends(get_plant_repository)],
    machine_repo: Annotated[MachineRepository, Depends(get_machine_repository)],
    implementation_repo: Annotated[
        ImplementationRepository, Depends(get_implementation_repository)
    ],
    issue_repo: Annotated[IssueRepository, Depends(get_issue_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IssueResponse:
    await _get_project_or_404(project_repo, project_id)
    await _validate_hierarchy_link(
        project_id=project_id,
        plant_id=payload.plant_id,
        machine_id=payload.machine_id,
        implementation_id=payload.implementation_id,
        plant_repo=plant_repo,
        machine_repo=machine_repo,
        implementation_repo=implementation_repo,
    )

    issue = await issue_repo.create(
        project_id=project_id,
        title=payload.title,
        description=payload.description,
        issue_type=payload.issue_type,
        priority=payload.priority,
        created_by=current_user.id,
        milestone_id=payload.milestone_id,
        assignee_id=payload.assignee_id,
        plant_id=payload.plant_id,
        machine_id=payload.machine_id,
        implementation_id=payload.implementation_id,
    )
    await audit.record(
        project_id=project_id,
        actor_id=current_user.id,
        entity_type="issue",
        entity_id=issue.id,
        action="issue.created",
        diff={"title": issue.title, "issue_type": issue.issue_type.value},
    )
    await session.commit()
    return _issue_response(issue)


@router.get("/projects/{project_id}/issues", response_model=list[IssueResponse])
async def list_project_issues(
    project_id: UUID,
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    issue_repo: Annotated[IssueRepository, Depends(get_issue_repository)],
    status_filter: Annotated[IssueStatus | None, Query(alias="status")] = None,
    assignee_id: Annotated[UUID | None, Query()] = None,
    label_id: Annotated[UUID | None, Query()] = None,
    milestone_id: Annotated[UUID | None, Query()] = None,
) -> list[IssueResponse]:
    await _get_project_or_404(project_repo, project_id)
    issues = await issue_repo.list_for_project(
        project_id,
        status=status_filter,
        assignee_id=assignee_id,
        label_id=label_id,
        milestone_id=milestone_id,
    )
    return [_issue_response(issue) for issue in issues]


@router.get("/issues/{issue_id}", response_model=IssueResponse)
async def get_issue(
    issue_id: UUID,
    issue_repo: Annotated[IssueRepository, Depends(get_issue_repository)],
) -> IssueResponse:
    issue = await _get_issue_or_404(issue_repo, issue_id)
    return _issue_response(issue)


@router.patch("/issues/{issue_id}", response_model=IssueResponse)
async def update_issue(
    issue_id: UUID,
    payload: IssueUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    plant_repo: Annotated[PlantRepository, Depends(get_plant_repository)],
    machine_repo: Annotated[MachineRepository, Depends(get_machine_repository)],
    implementation_repo: Annotated[
        ImplementationRepository, Depends(get_implementation_repository)
    ],
    issue_repo: Annotated[IssueRepository, Depends(get_issue_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IssueResponse:
    issue = await _get_issue_or_404(issue_repo, issue_id)
    await _validate_hierarchy_link(
        project_id=issue.project_id,
        plant_id=payload.plant_id,
        machine_id=payload.machine_id,
        implementation_id=payload.implementation_id,
        plant_repo=plant_repo,
        machine_repo=machine_repo,
        implementation_repo=implementation_repo,
    )

    updated = await issue_repo.update(
        issue_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        issue_type=payload.issue_type,
        milestone_id=payload.milestone_id,
        assignee_id=payload.assignee_id,
        plant_id=payload.plant_id,
        machine_id=payload.machine_id,
        implementation_id=payload.implementation_id,
    )
    await audit.record(
        project_id=issue.project_id,
        actor_id=current_user.id,
        entity_type="issue",
        entity_id=issue_id,
        action="issue.updated",
        diff={"title": updated.title},
    )
    await session.commit()
    return _issue_response(updated)


@router.patch("/issues/{issue_id}/status", response_model=IssueResponse)
async def update_issue_status(
    issue_id: UUID,
    payload: IssueStatusUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    issue_repo: Annotated[IssueRepository, Depends(get_issue_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IssueResponse:
    issue = await _get_issue_or_404(issue_repo, issue_id)
    updated = await issue_repo.set_status(issue_id, payload.status)
    await audit.record(
        project_id=issue.project_id,
        actor_id=current_user.id,
        entity_type="issue",
        entity_id=issue_id,
        action="issue.status_changed",
        diff={"from": issue.status.value, "to": updated.status.value},
    )
    await session.commit()
    return _issue_response(updated)


@router.post("/issues/{issue_id}/labels", response_model=IssueResponse)
async def attach_issue_label(
    issue_id: UUID,
    payload: IssueLabelAttachRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    issue_repo: Annotated[IssueRepository, Depends(get_issue_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IssueResponse:
    issue = await _get_issue_or_404(issue_repo, issue_id)
    updated = await issue_repo.attach_label(issue_id, payload.label_id)
    await audit.record(
        project_id=issue.project_id,
        actor_id=current_user.id,
        entity_type="issue",
        entity_id=issue_id,
        action="issue.label_attached",
        diff={"label_id": str(payload.label_id)},
    )
    await session.commit()
    return _issue_response(updated)


@router.delete("/issues/{issue_id}/labels/{label_id}", response_model=IssueResponse)
async def detach_issue_label(
    issue_id: UUID,
    label_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    issue_repo: Annotated[IssueRepository, Depends(get_issue_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IssueResponse:
    issue = await _get_issue_or_404(issue_repo, issue_id)
    updated = await issue_repo.detach_label(issue_id, label_id)
    await audit.record(
        project_id=issue.project_id,
        actor_id=current_user.id,
        entity_type="issue",
        entity_id=issue_id,
        action="issue.label_detached",
        diff={"label_id": str(label_id)},
    )
    await session.commit()
    return _issue_response(updated)
