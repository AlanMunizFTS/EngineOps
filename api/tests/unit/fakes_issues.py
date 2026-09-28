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
)
from ops_platform.domain.ports.issue_comment_repository import IssueCommentRepository
from ops_platform.domain.ports.issue_repository import IssueRepository
from ops_platform.domain.ports.kanban_repository import KanbanRepository
from ops_platform.domain.ports.label_repository import LabelRepository


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
        assignee_id: UUID | None,
        parent_issue_id: UUID | None = None,
        start_date: date | None = None,
        due_date: date | None = None,
    ) -> Issue:
        issue = Issue(
            id=uuid.uuid4(),
            project_id=project_id,
            title=title,
            description=description,
            status=IssueStatus.BACKLOG,
            priority=priority,
            issue_type=issue_type,
            assignee_id=assignee_id,
            created_by=created_by,
            created_at=datetime.now(UTC),
            closed_at=None,
            parent_issue_id=parent_issue_id,
            parent_assigned_at=datetime.now(UTC) if parent_issue_id is not None else None,
            start_date=start_date,
            due_date=due_date,
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
    ) -> list[Issue]:
        results = [issue for issue in self._issues.values() if issue.project_id == project_id]
        if status is not None:
            results = [issue for issue in results if issue.status == status]
        if assignee_id is not None:
            results = [issue for issue in results if issue.assignee_id == assignee_id]
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
        assignee_id: UUID | None,
        parent_issue_id: UUID | None = None,
        start_date: date | None = None,
        due_date: date | None = None,
        closed_at: date | None = None,
    ) -> Issue:
        current = self._issues[issue_id]
        parent_assigned_at = current.parent_assigned_at
        if parent_issue_id != current.parent_issue_id:
            parent_assigned_at = datetime.now(UTC) if parent_issue_id is not None else None
        updated = replace(
            current,
            title=title,
            description=description,
            priority=priority,
            issue_type=issue_type,
            assignee_id=assignee_id,
            parent_issue_id=parent_issue_id,
            parent_assigned_at=parent_assigned_at,
            start_date=start_date,
            due_date=due_date,
            closed_at=(
                datetime.combine(closed_at, datetime.min.time(), tzinfo=UTC) if closed_at else None
            ),
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

    async def delete(self, issue_id: UUID) -> None:
        self._issues.pop(issue_id, None)
        for child_id, child in list(self._issues.items()):
            if child.parent_issue_id == issue_id:
                self._issues[child_id] = replace(
                    child, parent_issue_id=None, parent_assigned_at=None
                )


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
                maps_to_statuses=[maps_to_status],
            )
            for order_index, (name, maps_to_status) in enumerate(self._DEFAULT_COLUMNS)
        ]
        board = KanbanBoard(id=board_id, project_id=project_id, name="Board", columns=columns)
        self._boards[board_id] = board
        return board

    async def create_board(self, project_id: UUID, name: str) -> KanbanBoard:
        board_id = uuid.uuid4()
        columns = [
            KanbanColumn(
                id=uuid.uuid4(),
                board_id=board_id,
                name=col_name,
                order_index=order_index,
                maps_to_statuses=[maps_to_status],
            )
            for order_index, (col_name, maps_to_status) in enumerate(self._DEFAULT_COLUMNS)
        ]
        board = KanbanBoard(id=board_id, project_id=project_id, name=name, columns=columns)
        self._boards[board_id] = board
        return board

    async def get(self, board_id: UUID) -> KanbanBoard | None:
        return self._boards.get(board_id)

    async def list_for_project(self, project_id: UUID) -> list[KanbanBoard]:
        return sorted(
            (b for b in self._boards.values() if b.project_id == project_id), key=lambda b: b.name
        )

    async def rename_board(self, board_id: UUID, name: str) -> KanbanBoard:
        updated = replace(self._boards[board_id], name=name)
        self._boards[board_id] = updated
        return updated

    async def delete_board(self, board_id: UUID) -> None:
        self._boards.pop(board_id, None)

    async def get_column(self, column_id: UUID) -> KanbanColumn | None:
        for board in self._boards.values():
            for column in board.columns:
                if column.id == column_id:
                    return column
        return None

    async def create_column(
        self, board_id: UUID, name: str, maps_to_statuses: list[IssueStatus]
    ) -> KanbanColumn:
        board = self._boards[board_id]
        column = KanbanColumn(
            id=uuid.uuid4(),
            board_id=board_id,
            name=name,
            order_index=len(board.columns),
            maps_to_statuses=maps_to_statuses,
        )
        self._boards[board_id] = replace(board, columns=[*board.columns, column])
        return column

    async def update_column(
        self, column_id: UUID, name: str, maps_to_statuses: list[IssueStatus]
    ) -> KanbanColumn:
        for board_id, board in self._boards.items():
            for index, column in enumerate(board.columns):
                if column.id == column_id:
                    updated = replace(column, name=name, maps_to_statuses=maps_to_statuses)
                    new_columns = list(board.columns)
                    new_columns[index] = updated
                    self._boards[board_id] = replace(board, columns=new_columns)
                    return updated
        raise ValueError(f"kanban column {column_id} not found")

    async def delete_column(self, column_id: UUID) -> None:
        for board_id, board in self._boards.items():
            if any(column.id == column_id for column in board.columns):
                new_columns = [c for c in board.columns if c.id != column_id]
                self._boards[board_id] = replace(board, columns=new_columns)
                return

    async def reorder_columns(self, board_id: UUID, ordered_column_ids: list[UUID]) -> KanbanBoard:
        board = self._boards[board_id]
        columns_by_id = {column.id: column for column in board.columns}
        new_columns = []
        for index, column_id in enumerate(ordered_column_ids):
            if column_id not in columns_by_id:
                raise ValueError(f"column {column_id} does not belong to board {board_id}")
            new_columns.append(replace(columns_by_id[column_id], order_index=index))
        updated = replace(board, columns=new_columns)
        self._boards[board_id] = updated
        return updated
