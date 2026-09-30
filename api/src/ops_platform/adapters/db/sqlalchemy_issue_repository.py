from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ops_platform.adapters.db.orm_models_issues import IssueLabelORM, IssueORM, LabelORM
from ops_platform.domain.entities import Issue, IssuePriority, IssueStatus, IssueType, Label
from ops_platform.domain.ports.issue_repository import IssueRepository


def _to_label(orm_label: LabelORM) -> Label:
    return Label(
        id=orm_label.id,
        project_id=orm_label.project_id,
        name=orm_label.name,
        color=orm_label.color,
    )


def _to_entity(orm_issue: IssueORM) -> Issue:
    return Issue(
        id=orm_issue.id,
        project_id=orm_issue.project_id,
        title=orm_issue.title,
        description=orm_issue.description,
        status=orm_issue.status,
        priority=orm_issue.priority,
        issue_type=orm_issue.issue_type,
        assignee_id=orm_issue.assignee_id,
        created_by=orm_issue.created_by,
        created_at=orm_issue.created_at,
        closed_at=orm_issue.closed_at,
        parent_issue_id=orm_issue.parent_issue_id,
        parent_assigned_at=orm_issue.parent_assigned_at,
        start_date=orm_issue.start_date,
        due_date=orm_issue.due_date,
        labels=[_to_label(label) for label in orm_issue.labels],
    )


class SqlAlchemyIssueRepository(IssueRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _get_or_raise(self, issue_id: UUID) -> IssueORM:
        orm_issue = await self._session.get(IssueORM, issue_id)
        if orm_issue is None:
            raise ValueError(f"issue {issue_id} not found")
        return orm_issue

    async def create(
        self,
        *,
        project_id: UUID,
        title: str,
        description: str | None,
        issue_type: IssueType,
        priority: IssuePriority,
        created_by: UUID,
        assignee_id: UUID | None,
        parent_issue_id: UUID | None = None,
        start_date: date | None = None,
        due_date: date | None = None,
    ) -> Issue:
        orm_issue = IssueORM(
            project_id=project_id,
            title=title,
            description=description,
            issue_type=issue_type,
            priority=priority,
            created_by=created_by,
            assignee_id=assignee_id,
            parent_issue_id=parent_issue_id,
            parent_assigned_at=datetime.now(UTC) if parent_issue_id is not None else None,
            start_date=start_date,
            due_date=due_date,
        )
        self._session.add(orm_issue)
        await self._session.flush()
        await self._session.refresh(orm_issue, attribute_names=["labels"])
        return _to_entity(orm_issue)

    async def get(self, issue_id: UUID) -> Issue | None:
        orm_issue = await self._session.get(IssueORM, issue_id)
        return _to_entity(orm_issue) if orm_issue else None

    async def list_for_project(
        self,
        project_id: UUID,
        *,
        status: IssueStatus | None = None,
        assignee_id: UUID | None = None,
        label_id: UUID | None = None,
    ) -> list[Issue]:
        query = select(IssueORM).where(IssueORM.project_id == project_id)
        if status is not None:
            query = query.where(IssueORM.status == status)
        if assignee_id is not None:
            query = query.where(IssueORM.assignee_id == assignee_id)
        if label_id is not None:
            query = query.join(IssueLabelORM, IssueLabelORM.issue_id == IssueORM.id).where(
                IssueLabelORM.label_id == label_id
            )
        query = query.order_by(IssueORM.created_at.desc())
        result = await self._session.execute(query)
        return [_to_entity(row) for row in result.scalars().all()]

    async def list_pending_for_assignee(self, assignee_id: UUID) -> list[Issue]:
        query = (
            select(IssueORM)
            .where(
                IssueORM.assignee_id == assignee_id,
                IssueORM.status != IssueStatus.DONE,
            )
            .order_by(IssueORM.created_at.desc())
        )
        result = await self._session.execute(query)
        return [_to_entity(row) for row in result.scalars().all()]

    async def update(
        self,
        issue_id: UUID,
        *,
        title: str,
        description: str | None,
        priority: IssuePriority,
        issue_type: IssueType,
        assignee_id: UUID | None,
        parent_issue_id: UUID | None = None,
        start_date: date | None = None,
        due_date: date | None = None,
        closed_at: date | None = None,
    ) -> Issue:
        orm_issue = await self._get_or_raise(issue_id)
        orm_issue.title = title
        orm_issue.description = description
        orm_issue.priority = priority
        orm_issue.issue_type = issue_type
        orm_issue.assignee_id = assignee_id
        if parent_issue_id != orm_issue.parent_issue_id:
            orm_issue.parent_assigned_at = (
                datetime.now(UTC) if parent_issue_id is not None else None
            )
        orm_issue.parent_issue_id = parent_issue_id
        orm_issue.start_date = start_date
        orm_issue.due_date = due_date
        orm_issue.closed_at = (
            datetime.combine(closed_at, datetime.min.time(), tzinfo=UTC) if closed_at else None
        )
        await self._session.flush()
        await self._session.refresh(orm_issue, attribute_names=["labels"])
        return _to_entity(orm_issue)

    async def set_status(self, issue_id: UUID, status: IssueStatus) -> Issue:
        orm_issue = await self._get_or_raise(issue_id)
        orm_issue.status = status
        orm_issue.closed_at = datetime.now(UTC) if status == IssueStatus.DONE else None
        await self._session.flush()
        await self._session.refresh(orm_issue, attribute_names=["labels"])
        return _to_entity(orm_issue)

    async def attach_label(self, issue_id: UUID, label_id: UUID) -> Issue:
        orm_issue = await self._get_or_raise(issue_id)
        already_attached = any(label.id == label_id for label in orm_issue.labels)
        if not already_attached:
            self._session.add(IssueLabelORM(issue_id=issue_id, label_id=label_id))
            await self._session.flush()
            await self._session.refresh(orm_issue, attribute_names=["labels"])
        return _to_entity(orm_issue)

    async def detach_label(self, issue_id: UUID, label_id: UUID) -> Issue:
        orm_issue = await self._get_or_raise(issue_id)
        await self._session.execute(
            delete(IssueLabelORM).where(
                IssueLabelORM.issue_id == issue_id, IssueLabelORM.label_id == label_id
            )
        )
        await self._session.flush()
        await self._session.refresh(orm_issue, attribute_names=["labels"])
        return _to_entity(orm_issue)

    async def delete(self, issue_id: UUID) -> None:
        orm_issue = await self._get_or_raise(issue_id)
        await self._session.delete(orm_issue)
        await self._session.flush()
