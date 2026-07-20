from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.api.deps import (
    get_audit_recorder,
    get_current_user,
    get_issue_comment_repository,
    get_issue_repository,
)
from ops_platform.db.session import get_db_session
from ops_platform.domain.entities import IssueComment, User
from ops_platform.domain.ports.audit_recorder import AuditRecorder
from ops_platform.domain.ports.issue_comment_repository import IssueCommentRepository
from ops_platform.domain.ports.issue_repository import IssueRepository
from ops_platform.schemas.issues import (
    IssueCommentCreateRequest,
    IssueCommentResponse,
    IssueCommentUpdateRequest,
)

router = APIRouter(tags=["issue-comments"])


def _comment_response(comment: IssueComment) -> IssueCommentResponse:
    return IssueCommentResponse(
        id=comment.id,
        issue_id=comment.issue_id,
        author_id=comment.author_id,
        body=comment.body,
        created_at=comment.created_at,
        edited_at=comment.edited_at,
    )


@router.post(
    "/issues/{issue_id}/comments",
    response_model=IssueCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_issue_comment(
    issue_id: UUID,
    payload: IssueCommentCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    issue_repo: Annotated[IssueRepository, Depends(get_issue_repository)],
    comment_repo: Annotated[IssueCommentRepository, Depends(get_issue_comment_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IssueCommentResponse:
    issue = await issue_repo.get(issue_id)
    if issue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    comment = await comment_repo.create(issue_id, current_user.id, payload.body)
    await audit.record(
        project_id=issue.project_id,
        actor_id=current_user.id,
        entity_type="issue_comment",
        entity_id=comment.id,
        action="issue.comment_added",
        diff={"issue_id": str(issue_id)},
    )
    await session.commit()
    return _comment_response(comment)


@router.get("/issues/{issue_id}/comments", response_model=list[IssueCommentResponse])
async def list_issue_comments(
    issue_id: UUID,
    issue_repo: Annotated[IssueRepository, Depends(get_issue_repository)],
    comment_repo: Annotated[IssueCommentRepository, Depends(get_issue_comment_repository)],
) -> list[IssueCommentResponse]:
    if await issue_repo.get(issue_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    comments = await comment_repo.list_for_issue(issue_id)
    return [_comment_response(comment) for comment in comments]


@router.patch("/issue-comments/{comment_id}", response_model=IssueCommentResponse)
async def update_issue_comment(
    comment_id: UUID,
    payload: IssueCommentUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    comment_repo: Annotated[IssueCommentRepository, Depends(get_issue_comment_repository)],
    issue_repo: Annotated[IssueRepository, Depends(get_issue_repository)],
    audit: Annotated[AuditRecorder, Depends(get_audit_recorder)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IssueCommentResponse:
    comment = await comment_repo.get(comment_id)
    if comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    issue = await issue_repo.get(comment.issue_id)
    if issue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    updated = await comment_repo.update_body(comment_id, payload.body)
    await audit.record(
        project_id=issue.project_id,
        actor_id=current_user.id,
        entity_type="issue_comment",
        entity_id=comment_id,
        action="issue.comment_edited",
        diff={"issue_id": str(comment.issue_id)},
    )
    await session.commit()
    return _comment_response(updated)
