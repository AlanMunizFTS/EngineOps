from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models_issues import IssueCommentORM
from ops_platform.domain.entities import IssueComment
from ops_platform.domain.ports.issue_comment_repository import IssueCommentRepository


def _to_entity(orm_comment: IssueCommentORM) -> IssueComment:
    return IssueComment(
        id=orm_comment.id,
        issue_id=orm_comment.issue_id,
        author_id=orm_comment.author_id,
        body=orm_comment.body,
        created_at=orm_comment.created_at,
        edited_at=orm_comment.edited_at,
    )


class SqlAlchemyIssueCommentRepository(IssueCommentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, issue_id: UUID, author_id: UUID, body: str) -> IssueComment:
        orm_comment = IssueCommentORM(issue_id=issue_id, author_id=author_id, body=body)
        self._session.add(orm_comment)
        await self._session.flush()
        await self._session.refresh(orm_comment)
        return _to_entity(orm_comment)

    async def get(self, comment_id: UUID) -> IssueComment | None:
        orm_comment = await self._session.get(IssueCommentORM, comment_id)
        return _to_entity(orm_comment) if orm_comment else None

    async def list_for_issue(self, issue_id: UUID) -> list[IssueComment]:
        result = await self._session.execute(
            select(IssueCommentORM)
            .where(IssueCommentORM.issue_id == issue_id)
            .order_by(IssueCommentORM.created_at)
        )
        return [_to_entity(row) for row in result.scalars().all()]

    async def update_body(self, comment_id: UUID, body: str) -> IssueComment:
        orm_comment = await self._session.get(IssueCommentORM, comment_id)
        if orm_comment is None:
            raise ValueError(f"issue comment {comment_id} not found")
        orm_comment.body = body
        orm_comment.edited_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(orm_comment)
        return _to_entity(orm_comment)
