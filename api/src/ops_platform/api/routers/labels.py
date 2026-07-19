from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.api.deps import (
    get_audit_recorder,
    get_current_user,
    get_label_repository,
    get_project_repository,
)
from ops_platform.db.session import get_db_session
from ops_platform.domain.entities import Label, User
from ops_platform.domain.ports.audit_recorder import AuditRecorder
from ops_platform.domain.ports.label_repository import LabelRepository
from ops_platform.domain.ports.project_repository import ProjectRepository
from ops_platform.schemas.labels import LabelCreateRequest, LabelResponse

router = APIRouter(tags=["labels"])


def _label_response(label: Label) -> LabelResponse:
    return LabelResponse(
        id=label.id, project_id=label.project_id, name=label.name, color=label.color
    )


async def _get_project_or_404(project_repo: ProjectRepository, project_id: UUID) -> None:
    if await project_repo.get(project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


@router.post(
    "/projects/{project_id}/labels",
    response_model=LabelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_label(
    project_id: UUID,
    payload: LabelCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    label_repo: Annotated[LabelRepository, Depends(get_label_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LabelResponse:
    await _get_project_or_404(project_repo, project_id)

    label = await label_repo.create(project_id=project_id, name=payload.name, color=payload.color)
    await audit.record(
        project_id=project_id,
        actor_id=current_user.id,
        entity_type="label",
        entity_id=label.id,
        action="label.created",
        diff={"name": label.name, "color": label.color},
    )
    await session.commit()
    return _label_response(label)


@router.get("/projects/{project_id}/labels", response_model=list[LabelResponse])
async def list_project_labels(
    project_id: UUID,
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    label_repo: Annotated[LabelRepository, Depends(get_label_repository)],
) -> list[LabelResponse]:
    await _get_project_or_404(project_repo, project_id)
    labels = await label_repo.list_for_project(project_id)
    return [_label_response(label) for label in labels]
