"""In-memory fakes for the Phase 2 (task-tracking) repository ports - split out
from fakes.py to keep that module under the ~400-line limit (CLAUDE.md §3)."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, date, datetime
from uuid import UUID

from ops_platform.domain.entities import (
    KanbanBoard,
    KanbanColumn,
    Label,
    Milestone,
    Task,
    TaskComment,
    TaskPriority,
    TaskStatus,
    TaskType,
)
from ops_platform.domain.ports.kanban_repository import KanbanRepository
from ops_platform.domain.ports.label_repository import LabelRepository
from ops_platform.domain.ports.milestone_repository import MilestoneRepository
from ops_platform.domain.ports.task_comment_repository import TaskCommentRepository
from ops_platform.domain.ports.task_repository import TaskRepository


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


class FakeTaskCommentRepository(TaskCommentRepository):
    def __init__(self) -> None:
        self._comments: dict[UUID, TaskComment] = {}

    async def create(self, task_id: UUID, author_id: UUID, body: str) -> TaskComment:
        comment = TaskComment(
            id=uuid.uuid4(),
            task_id=task_id,
            author_id=author_id,
            body=body,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self._comments[comment.id] = comment
        return comment

    async def get(self, comment_id: UUID) -> TaskComment | None:
        return self._comments.get(comment_id)

    async def list_for_task(self, task_id: UUID) -> list[TaskComment]:
        return [c for c in self._comments.values() if c.task_id == task_id]

    async def update_body(self, comment_id: UUID, body: str) -> TaskComment:
        updated = replace(self._comments[comment_id], body=body, updated_at=datetime.now(UTC))
        self._comments[comment_id] = updated
        return updated


class FakeTaskRepository(TaskRepository):
    """Takes the label repository fake to resolve label_id -> Label when
    attaching, mirroring the SQL adapter's join against labels."""

    def __init__(self, label_repository: FakeLabelRepository) -> None:
        self._label_repository = label_repository
        self._tasks: dict[UUID, Task] = {}

    async def create(
        self,
        *,
        project_id: UUID,
        title: str,
        description: str | None,
        task_type: TaskType,
        priority: TaskPriority,
        created_by: UUID | None,
        assignee_id: UUID | None,
        assignee_ids: list[UUID] | None = None,
        milestone_id: UUID | None = None,
        parent_task_id: UUID | None = None,
        start_date: date | None = None,
        due_date: date | None = None,
    ) -> Task:
        now = datetime.now(UTC)
        normalized_assignee_ids = list(
            dict.fromkeys(assignee_ids or ([assignee_id] if assignee_id else []))
        )
        task = Task(
            id=uuid.uuid4(),
            project_id=project_id,
            title=title,
            description=description,
            status=TaskStatus.BACKLOG,
            priority=priority,
            task_type=task_type,
            assignee_id=normalized_assignee_ids[0] if normalized_assignee_ids else None,
            assignee_ids=normalized_assignee_ids,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            closed_at=None,
            milestone_id=milestone_id,
            parent_task_id=parent_task_id,
            parent_assigned_at=datetime.now(UTC) if parent_task_id is not None else None,
            start_date=start_date,
            due_date=due_date,
        )
        self._tasks[task.id] = task
        return task

    async def get(self, task_id: UUID) -> Task | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        children = await self.list_subtasks(task_id)
        return replace(
            task,
            subtasks_total=len(children),
            subtasks_completed=sum(child.status == TaskStatus.DONE for child in children),
        )

    async def list_for_project(
        self,
        project_id: UUID,
        *,
        include_subtasks: bool = False,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        task_type: TaskType | None = None,
        assignee_id: UUID | None = None,
        milestone_id: UUID | None = None,
        label_id: UUID | None = None,
    ) -> list[Task]:
        results = [task for task in self._tasks.values() if task.project_id == project_id]
        if not include_subtasks:
            results = [task for task in results if task.parent_task_id is None]
        if status is not None:
            results = [task for task in results if task.status == status]
        if priority is not None:
            results = [task for task in results if task.priority == priority]
        if task_type is not None:
            results = [task for task in results if task.task_type == task_type]
        if assignee_id is not None:
            results = [task for task in results if assignee_id in task.assignee_ids]
        if milestone_id is not None:
            results = [task for task in results if task.milestone_id == milestone_id]
        if label_id is not None:
            results = [
                task for task in results if any(label.id == label_id for label in task.labels)
            ]
        return [await self.get(task.id) for task in results]  # type: ignore[misc]

    async def list_pending_for_assignee(self, assignee_id: UUID) -> list[Task]:
        return [
            task
            for task in self._tasks.values()
            if assignee_id in task.assignee_ids
            and task.status != TaskStatus.DONE
            and task.parent_task_id is None
        ]

    async def list_subtasks(self, task_id: UUID) -> list[Task]:
        return [task for task in self._tasks.values() if task.parent_task_id == task_id]

    async def list_by_milestone(self, milestone_id: UUID) -> list[Task]:
        return [
            task
            for task in self._tasks.values()
            if task.milestone_id == milestone_id and task.parent_task_id is None
        ]

    async def has_children(self, task_id: UUID) -> bool:
        return bool(await self.list_subtasks(task_id))

    async def update(
        self,
        task_id: UUID,
        **changes,
    ) -> Task:
        current = self._tasks[task_id]
        if "assignee_ids" in changes:
            assignee_ids = list(dict.fromkeys(changes["assignee_ids"] or []))
            changes["assignee_ids"] = assignee_ids
            changes["assignee_id"] = assignee_ids[0] if assignee_ids else None
        elif "assignee_id" in changes:
            assignee_id = changes["assignee_id"]
            changes["assignee_ids"] = [assignee_id] if assignee_id else []
        if isinstance(changes.get("closed_at"), date):
            changes["closed_at"] = datetime.combine(
                changes["closed_at"], datetime.min.time(), tzinfo=UTC
            )
        updated = replace(current, **changes, updated_at=datetime.now(UTC))
        self._tasks[task_id] = updated
        return updated

    async def reparent(self, task_id: UUID, parent_task_id: UUID | None) -> Task:
        updated = replace(
            self._tasks[task_id],
            parent_task_id=parent_task_id,
            milestone_id=None,
            parent_assigned_at=datetime.now(UTC) if parent_task_id else None,
            updated_at=datetime.now(UTC),
        )
        self._tasks[task_id] = updated
        return updated

    async def set_status(self, task_id: UUID, status: TaskStatus) -> Task:
        closed_at = datetime.now(UTC) if status == TaskStatus.DONE else None
        updated = replace(self._tasks[task_id], status=status, closed_at=closed_at)
        self._tasks[task_id] = updated
        return updated

    async def attach_label(self, task_id: UUID, label_id: UUID) -> Task:
        task = self._tasks[task_id]
        if not any(label.id == label_id for label in task.labels):
            label = next(
                label
                for label in await self._label_repository.list_for_project(task.project_id)
                if label.id == label_id
            )
            task = replace(task, labels=[*task.labels, label])
            self._tasks[task_id] = task
        return task

    async def detach_label(self, task_id: UUID, label_id: UUID) -> Task:
        task = self._tasks[task_id]
        updated = replace(task, labels=[label for label in task.labels if label.id != label_id])
        self._tasks[task_id] = updated
        return updated

    async def delete(self, task_id: UUID) -> None:
        self._tasks.pop(task_id, None)


class FakeMilestoneRepository(MilestoneRepository):
    def __init__(self, tasks: FakeTaskRepository) -> None:
        self._milestones: dict[UUID, Milestone] = {}
        self._tasks = tasks

    async def _with_progress(self, milestone: Milestone) -> Milestone:
        tasks = await self._tasks.list_by_milestone(milestone.id)
        return replace(
            milestone,
            total_tasks=len(tasks),
            completed_tasks=sum(task.status == TaskStatus.DONE for task in tasks),
        )

    async def create(self, **values) -> Milestone:
        now = datetime.now(UTC)
        milestone = Milestone(id=uuid.uuid4(), created_at=now, updated_at=now, **values)
        self._milestones[milestone.id] = milestone
        return await self._with_progress(milestone)

    async def get(self, milestone_id: UUID) -> Milestone | None:
        milestone = self._milestones.get(milestone_id)
        return await self._with_progress(milestone) if milestone else None

    async def list_for_project(self, project_id: UUID) -> list[Milestone]:
        return [
            await self._with_progress(milestone)
            for milestone in self._milestones.values()
            if milestone.project_id == project_id
        ]

    async def update(self, milestone_id: UUID, **changes) -> Milestone:
        updated = replace(self._milestones[milestone_id], **changes, updated_at=datetime.now(UTC))
        self._milestones[milestone_id] = updated
        return await self._with_progress(updated)

    async def delete(self, milestone_id: UUID) -> None:
        self._milestones.pop(milestone_id)
        for task_id, task in list(self._tasks._tasks.items()):
            if task.milestone_id == milestone_id:
                self._tasks._tasks[task_id] = replace(task, milestone_id=None)


class FakeKanbanRepository(KanbanRepository):
    _DEFAULT_COLUMNS: list[tuple[str, TaskStatus]] = [
        ("Backlog", TaskStatus.BACKLOG),
        ("To Do", TaskStatus.TODO),
        ("In Progress", TaskStatus.IN_PROGRESS),
        ("In Review", TaskStatus.IN_REVIEW),
        ("Done", TaskStatus.DONE),
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
        self, board_id: UUID, name: str, maps_to_statuses: list[TaskStatus]
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
        self, column_id: UUID, name: str, maps_to_statuses: list[TaskStatus]
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
