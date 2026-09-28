from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.api.deps import (
    get_audit_recorder,
    get_current_user,
    get_file_tree_repository,
    get_project_repository,
)
from ops_platform.db.session import get_db_session
from ops_platform.domain.entities import FileTreeNode, FileTreeNodeType, User
from ops_platform.domain.ports.audit_recorder import AuditRecorder
from ops_platform.domain.ports.file_tree_repository import FileTreeRepository
from ops_platform.domain.ports.project_repository import ProjectRepository
from ops_platform.schemas.file_tree import (
    FileTreeNodeCreateRequest,
    FileTreeNodeResponse,
    FileTreeNodeUpdateRequest,
)

router = APIRouter(tags=["file-tree"])


def _node_response(node: FileTreeNode) -> FileTreeNodeResponse:
    return FileTreeNodeResponse(
        id=node.id,
        project_id=node.project_id,
        parent_id=node.parent_id,
        node_type=node.node_type,
        name=node.name,
        url=node.url,
        content=node.content,
        created_by=node.created_by,
        created_at=node.created_at,
    )


async def _get_project_or_404(project_repo: ProjectRepository, project_id: UUID) -> None:
    if await project_repo.get(project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


@router.post(
    "/projects/{project_id}/tree",
    response_model=FileTreeNodeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_file_tree_node(
    project_id: UUID,
    payload: FileTreeNodeCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    file_tree_repo: Annotated[FileTreeRepository, Depends(get_file_tree_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FileTreeNodeResponse:
    await _get_project_or_404(project_repo, project_id)

    if payload.parent_id is not None:
        parent = await file_tree_repo.get(payload.parent_id)
        if (
            parent is None
            or parent.project_id != project_id
            or parent.node_type != FileTreeNodeType.FOLDER
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Parent folder not found"
            )

    node = await file_tree_repo.create_node(
        project_id=project_id,
        parent_id=payload.parent_id,
        node_type=payload.node_type,
        name=payload.name,
        url=payload.url,
        content=payload.content if payload.node_type == FileTreeNodeType.FILE else None,
        created_by=current_user.id,
    )
    await audit.record(
        project_id=project_id,
        actor_id=current_user.id,
        entity_type="file_tree_node",
        entity_id=node.id,
        action=f"file_tree.{node.node_type.value}_created",
        diff={"name": node.name},
    )
    await session.commit()
    return _node_response(node)


@router.get("/projects/{project_id}/tree", response_model=list[FileTreeNodeResponse])
async def list_file_tree(
    project_id: UUID,
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    file_tree_repo: Annotated[FileTreeRepository, Depends(get_file_tree_repository)],
) -> list[FileTreeNodeResponse]:
    await _get_project_or_404(project_repo, project_id)
    nodes = await file_tree_repo.list_for_project(project_id)
    return [_node_response(node) for node in nodes]


@router.patch("/projects/{project_id}/tree/{node_id}", response_model=FileTreeNodeResponse)
async def update_file_tree_node_content(
    project_id: UUID,
    node_id: UUID,
    payload: FileTreeNodeUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    file_tree_repo: Annotated[FileTreeRepository, Depends(get_file_tree_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FileTreeNodeResponse:
    await _get_project_or_404(project_repo, project_id)

    node = await file_tree_repo.get(node_id)
    if node is None or node.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    if node.node_type != FileTreeNodeType.FILE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only file nodes have editable content"
        )

    updated = await file_tree_repo.update_content(node_id, payload.content)
    await audit.record(
        project_id=project_id,
        actor_id=current_user.id,
        entity_type="file_tree_node",
        entity_id=node_id,
        action="file_tree.content_updated",
        diff={"name": node.name},
    )
    await session.commit()
    return _node_response(updated)


@router.delete("/projects/{project_id}/tree/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file_tree_node(
    project_id: UUID,
    node_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    project_repo: Annotated[ProjectRepository, Depends(get_project_repository)],
    file_tree_repo: Annotated[FileTreeRepository, Depends(get_file_tree_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    await _get_project_or_404(project_repo, project_id)

    node = await file_tree_repo.get(node_id)
    if node is None or node.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")

    await file_tree_repo.delete(node_id)
    await audit.record(
        project_id=project_id,
        actor_id=current_user.id,
        entity_type="file_tree_node",
        entity_id=node_id,
        action=f"file_tree.{node.node_type.value}_deleted",
        diff={"name": node.name},
    )
    await session.commit()
