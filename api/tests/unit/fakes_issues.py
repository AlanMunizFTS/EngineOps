"""In-memory fakes for the Phase 2 (issue-tracking) repository ports - split out
from fakes.py to keep that module under the ~400-line limit (CLAUDE.md §3)."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, date, datetime
from uuid import UUID

from ops_platform.domain.entities import (
    Issue,
    IssueComment,
    IssuePriority,
    IssueStatus,
    IssueType,
    KanbanBoard,
    KanbanColumn,
    Label,
    Milestone,
    MilestoneStatus,
)
from ops_platform.domain.ports.issue_comment_repository import IssueCommentRepository
from ops_platform.domain.ports.issue_repository import IssueRepository
from ops_platform.domain.ports.kanban_repository import KanbanRepository
from ops_platform.domain.ports.label_repository import LabelRepository
from ops_platform.domain.ports.milestone_repository import MilestoneRepository


class FakeLabelRepository(LabelRepository):
    def __init__(self) -> None:
        self._labels: dict[UUID, Label] = {}

    async def create(self, project_id: UUID, name: str, color: str) -> Label:
        label = Label(id=uuid.uuid4(), project_id=project_id, name=name, color=color)
        self._labels[label.id] = label
        return label

    async def get(self, label_id: UUID) -> Label | None:
        return self._labels.get(label_id)

    async def list_for_project(self, project_id: UUID) -> list[Label]:
        return [label for label in self._labels.values() if label.project_id == project_id]


class FakeMilestoneRepository(MilestoneRepository):
    def __init__(self) -> None:
        self._milestones: dict[UUID, Milestone] = {}

    async def create(
        self, project_id: UUID, title: str, description: str | None, due_date: date | None
    ) -> Milestone:
        milestone = Milestone(
            id=uuid.uuid4(),
            project_id=project_id,
            title=title,
            description=description,
            due_date=due_date,
            status=MilestoneStatus.OPEN,
            created_at=datetime.now(UTC),
        )
        self._milestones[milestone.id] = milestone
        return milestone

    async def get(self, milestone_id: UUID) -> Milestone | None:
        return self._milestones.get(milestone_id)

    async def list_for_project(self, project_id: UUID) -> list[Milestone]:
        return [m for m in self._milestones.values() if m.project_id == project_id]

    async def update_status(self, milestone_id: UUID, status: MilestoneStatus) -> Milestone:
        updated = replace(self._milestones[milestone_id], status=status)
        self._milestones[milestone_id] = updated
        return updated


class FakeIssueCommentRepository(IssueCommentRepository):
    def __init__(self) -> None:
        self._comments: dict[UUID, IssueComment] = {}

    async def create(self, issue_id: UUID, author_id: UUID, body: str) -> IssueComment:
        comment = IssueComment(
            id=uuid.uuid4(),
            issue_id=issue_id,
            author_id=author_id,
            body=body,
            created_at=datetime.now(UTC),
            edited_at=None,
        )
        self._comments[comment.id] = comment
        return comment

    async def get(self, comment_id: UUID) -> IssueComment | None:
        return self._comments.get(comment_id)

    async def list_for_issue(self, issue_id: UUID) -> list[IssueComment]:
        return [c for c in self._comments.values() if c.issue_id == issue_id]

    async def update_body(self, comment_id: UUID, body: str) -> IssueComment:
        updated = replace(self._comments[comment_id], body=body, edited_at=datetime.now(UTC))
        self._comments[comment_id] = updated
        return updated


class FakeIssueRepository(IssueRepository):
    """Takes the label repository fake to resolve label_id -> Label when
    attaching, mirroring the SQL adapter's join against labels."""

    def __init__(self, label_repository: FakeLabelRepository) -> None:
        self._label_repository = label_repository
        self._issues: dict[UUID, Issue] = {}

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
    ) -> Issue:
        issue = Issue(
            id=uuid.uuid4(),
            project_id=project_id,
            title=title,
            description=description,
            status=IssueStatus.BACKLOG,
            priority=priority,
            issue_type=issue_type,
            milestone_id=milestone_id,
            assignee_id=assignee_id,
            created_by=created_by,
            created_at=datetime.now(UTC),
            closed_at=None,
        )
        self._issues[issue.id] = issue
        return issue

    async def get(self, issue_id: UUID) -> Issue | None:
        return self._issues.get(issue_id)

    async def list_for_project(
        self,
        project_id: UUID,
        *,
        status: IssueStatus | None = None,
        assignee_id: UUID | None = None,
        label_id: UUID | None = None,
        milestone_id: UUID | None = None,
    ) -> list[Issue]:
        results = [issue for issue in self._issues.values() if issue.project_id == project_id]
        if status is not None:
            results = [issue for issue in results if issue.status == status]
        if assignee_id is not None:
            results = [issue for issue in results if issue.assignee_id == assignee_id]
        if milestone_id is not None:
            results = [issue for issue in results if issue.milestone_id == milestone_id]
        if label_id is not None:
            results = [
                issue for issue in results if any(label.id == label_id for label in issue.labels)
            ]
        return results

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
    ) -> Issue:
        updated = replace(
            self._issues[issue_id],
            title=title,
            description=description,
            priority=priority,
            issue_type=issue_type,
            milestone_id=milestone_id,
            assignee_id=assignee_id,
        )
        self._issues[issue_id] = updated
        return updated

    async def set_status(self, issue_id: UUID, status: IssueStatus) -> Issue:
        closed_at = datetime.now(UTC) if status == IssueStatus.DONE else None
        updated = replace(self._issues[issue_id], status=status, closed_at=closed_at)
        self._issues[issue_id] = updated
        return updated

    async def attach_label(self, issue_id: UUID, label_id: UUID) -> Issue:
        issue = self._issues[issue_id]
        if not any(label.id == label_id for label in issue.labels):
            label = next(
                label
                for label in await self._label_repository.list_for_project(issue.project_id)
                if label.id == label_id
            )
            issue = replace(issue, labels=[*issue.labels, label])
            self._issues[issue_id] = issue
        return issue

    async def detach_label(self, issue_id: UUID, label_id: UUID) -> Issue:
        issue = self._issues[issue_id]
        updated = replace(issue, labels=[label for label in issue.labels if label.id != label_id])
        self._issues[issue_id] = updated
        return updated


class FakeKanbanRepository(KanbanRepository):
    _DEFAULT_COLUMNS: list[tuple[str, IssueStatus]] = [
        ("Backlog", IssueStatus.BACKLOG),
        ("To Do", IssueStatus.TODO),
        ("In Progress", IssueStatus.IN_PROGRESS),
        ("In Review", IssueStatus.IN_REVIEW),
        ("Done", IssueStatus.DONE),
    ]

    def __init__(self) -> None:
        self._boards: dict[UUID, KanbanBoard] = {}

    async def create_default_board(self, project_id: UUID) -> KanbanBoard:
        board_id = uuid.uuid4()
        columns = [
            KanbanColumn(
                id=uuid.uuid4(),
                board_id=board_id,
                name=name,
                order_index=order_index,
                maps_to_status=maps_to_status,
            )
            for order_index, (name, maps_to_status) in enumerate(self._DEFAULT_COLUMNS)
        ]
        board = KanbanBoard(id=board_id, project_id=project_id, name="Board", columns=columns)
        self._boards[project_id] = board
        return board

    async def get_for_project(self, project_id: UUID) -> KanbanBoard | None:
        return self._boards.get(project_id)
