from __future__ import annotations

from datetime import UTC, datetime
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
        plant_id=orm_issue.plant_id,
        machine_id=orm_issue.machine_id,
        implementation_id=orm_issue.implementation_id,
        title=orm_issue.title,
        description=orm_issue.description,
        status=orm_issue.status,
        priority=orm_issue.priority,
        issue_type=orm_issue.issue_type,
        milestone_id=orm_issue.milestone_id,
        assignee_id=orm_issue.assignee_id,
        created_by=orm_issue.created_by,
        created_at=orm_issue.created_at,
        closed_at=orm_issue.closed_at,
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
        milestone_id: UUID | None,
        assignee_id: UUID | None,
        plant_id: UUID | None,
        machine_id: UUID | None,
        implementation_id: UUID | None,
    ) -> Issue:
        orm_issue = IssueORM(
            project_id=project_id,
            title=title,
            description=description,
            issue_type=issue_type,
            priority=priority,
            created_by=created_by,
            milestone_id=milestone_id,
            assignee_id=assignee_id,
            plant_id=plant_id,
            machine_id=machine_id,
            implementation_id=implementation_id,
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
        milestone_id: UUID | None = None,
    ) -> list[Issue]:
        query = select(IssueORM).where(IssueORM.project_id == project_id)
        if status is not None:
            query = query.where(IssueORM.status == status)
        if assignee_id is not None:
            query = query.where(IssueORM.assignee_id == assignee_id)
        if milestone_id is not None:
            query = query.where(IssueORM.milestone_id == milestone_id)
        if label_id is not None:
            query = query.join(IssueLabelORM, IssueLabelORM.issue_id == IssueORM.id).where(
                IssueLabelORM.label_id == label_id
            )
        query = query.order_by(IssueORM.created_at.desc())
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
        milestone_id: UUID | None,
        assignee_id: UUID | None,
        plant_id: UUID | None,
        machine_id: UUID | None,
        implementation_id: UUID | None,
    ) -> Issue:
        orm_issue = await self._get_or_raise(issue_id)
        orm_issue.title = title
        orm_issue.description = description
        orm_issue.priority = priority
        orm_issue.issue_type = issue_type
        orm_issue.milestone_id = milestone_id
        orm_issue.assignee_id = assignee_id
        orm_issue.plant_id = plant_id
        orm_issue.machine_id = machine_id
        orm_issue.implementation_id = implementation_id
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
