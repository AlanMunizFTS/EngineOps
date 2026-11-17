from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import UUID

from ops_platform.application.errors import ConflictError, NotFoundError, ValidationError
from ops_platform.domain.entities import Task, TaskPriority, TaskStatus, TaskType
from ops_platform.domain.ports.label_repository import LabelRepository
from ops_platform.domain.ports.milestone_repository import MilestoneRepository
from ops_platform.domain.ports.task_repository import TaskRepository
from ops_platform.domain.scheduling import today_in_business_timezone


class TaskService:
    """Single authority for Task/Subtask hierarchy and completion invariants."""

    def __init__(
        self,
        tasks: TaskRepository,
        milestones: MilestoneRepository,
        labels: LabelRepository,
    ) -> None:
        self.tasks = tasks
        self.milestones = milestones
        self.labels = labels

    async def get(self, task_id: UUID) -> Task:
        task = await self.tasks.get(task_id)
        if task is None:
            raise NotFoundError("Task not found")
        return task

    async def create_task(
        self,
        *,
        project_id: UUID,
        title: str,
        description: str | None = None,
        task_type: TaskType = TaskType.TASK,
        priority: TaskPriority = TaskPriority.MEDIUM,
        created_by: UUID | None = None,
        assignee_id: UUID | None = None,
        assignee_ids: list[UUID] | None = None,
        milestone_id: UUID | None = None,
        start_date: date | None = None,
        due_date: date | None = None,
        repeat_daily: bool = False,
    ) -> Task:
        if milestone_id is not None:
            await self._validate_milestone(project_id, milestone_id)
        normalized_assignee_ids = list(
            dict.fromkeys(
                assignee_ids
                if assignee_ids is not None
                else ([assignee_id] if assignee_id else [])
            )
        )
        return await self.tasks.create(
            project_id=project_id,
            title=title,
            description=description,
            task_type=task_type,
            priority=priority,
            created_by=created_by,
            assignee_id=normalized_assignee_ids[0] if normalized_assignee_ids else None,
            assignee_ids=normalized_assignee_ids,
            milestone_id=milestone_id,
            start_date=start_date,
            due_date=due_date,
            repeat_daily=repeat_daily,
        )

    async def create_subtask(
        self,
        parent_task_id: UUID,
        *,
        project_id: UUID,
        title: str,
        description: str | None = None,
        task_type: TaskType = TaskType.TASK,
        priority: TaskPriority = TaskPriority.MEDIUM,
        created_by: UUID | None = None,
        assignee_id: UUID | None = None,
        assignee_ids: list[UUID] | None = None,
        start_date: date | None = None,
        due_date: date | None = None,
        repeat_daily: bool = False,
    ) -> Task:
        parent = await self.tasks.get(parent_task_id)
        if parent is None:
            raise NotFoundError("Parent Task not found")
        if parent.project_id != project_id:
            raise ValidationError("Parent Task belongs to a different Project")
        if parent.is_subtask:
            raise ConflictError("Nested Subtasks are not allowed")
        if parent.status == TaskStatus.DONE:
            raise ConflictError("Reopen the parent task before adding a subtask")
        if parent.repeat_daily:
            raise ConflictError("Daily recurring tasks cannot contain subtasks")
        if repeat_daily:
            raise ConflictError("Subtasks cannot repeat daily")
        normalized_assignee_ids = list(
            dict.fromkeys(
                assignee_ids
                if assignee_ids is not None
                else ([assignee_id] if assignee_id else [])
            )
        )
        return await self.tasks.create(
            project_id=project_id,
            title=title,
            description=description,
            task_type=task_type,
            priority=priority,
            created_by=created_by,
            assignee_id=normalized_assignee_ids[0] if normalized_assignee_ids else None,
            assignee_ids=normalized_assignee_ids,
            parent_task_id=parent.id,
            milestone_id=None,
            start_date=start_date,
            due_date=due_date,
        )

    async def update_task(self, task_id: UUID, **changes: Any) -> Task:
        task = await self.get(task_id)
        if "assignee_ids" in changes:
            assignee_ids = list(dict.fromkeys(changes["assignee_ids"] or []))
            changes["assignee_ids"] = assignee_ids
            changes["assignee_id"] = assignee_ids[0] if assignee_ids else None
        elif "assignee_id" in changes:
            assignee_id = changes["assignee_id"]
            changes["assignee_ids"] = (
                [
                    assignee_id,
                    *(
                        existing_id
                        for existing_id in task.assignee_ids
                        if existing_id not in {task.assignee_id, assignee_id}
                    ),
                ]
                if assignee_id
                else []
            )
        if "parent_task_id" in changes:
            raise ValidationError("Use the parent operation to change Task hierarchy")
        if changes.get("repeat_daily"):
            if task.is_subtask:
                raise ConflictError("Subtasks cannot repeat daily")
            if await self.tasks.has_children(task_id):
                raise ConflictError("A task with subtasks cannot repeat daily")
        if "milestone_id" in changes:
            milestone_id = changes["milestone_id"]
            if task.is_subtask and milestone_id is not None:
                raise ConflictError("Subtasks cannot be assigned directly to a Milestone")
            if milestone_id is not None:
                await self._validate_milestone(task.project_id, milestone_id)
        return await self.tasks.update(task_id, **changes)

    async def change_status(self, task_id: UUID, new_status: TaskStatus) -> Task:
        task = await self.get(task_id)
        if task.status == new_status:
            return task
        if new_status == TaskStatus.DONE and task.is_top_level:
            children = await self.tasks.list_subtasks(task.id)
            if any(child.status != TaskStatus.DONE for child in children):
                raise ConflictError("Cannot complete task while subtasks remain incomplete")
        if task.is_subtask and new_status != TaskStatus.DONE:
            parent = await self.tasks.get(task.parent_task_id)  # type: ignore[arg-type]
            if parent is not None and parent.status == TaskStatus.DONE:
                raise ConflictError("Parent task must be reopened before reopening this subtask")
        updated = await self.tasks.set_status(task_id, new_status)
        if new_status == TaskStatus.DONE and task.repeat_daily:
            await self._create_next_daily_occurrence(task)
        return updated

    async def _create_next_daily_occurrence(self, task: Task) -> None:
        if await self.tasks.get_next_recurrence(task.id) is not None:
            return
        today = today_in_business_timezone()
        anchor = max(today, task.start_date or today, task.due_date or today)
        next_date = anchor + timedelta(days=1)
        next_task = await self.tasks.create(
            project_id=task.project_id,
            title=task.title,
            description=task.description,
            task_type=task.task_type,
            priority=task.priority,
            created_by=task.created_by,
            assignee_id=task.assignee_id,
            assignee_ids=task.assignee_ids,
            milestone_id=task.milestone_id,
            start_date=next_date if task.start_date is not None else None,
            due_date=next_date,
            repeat_daily=True,
            recurrence_parent_id=task.id,
        )
        for label in task.labels:
            await self.tasks.attach_label(next_task.id, label.id)
        await self.tasks.set_status(next_task.id, TaskStatus.TODO)

    async def delete_task(self, task_id: UUID) -> Task:
        task = await self.get(task_id)
        if await self.tasks.has_children(task_id):
            raise ConflictError("Task contains subtasks")
        await self.tasks.delete(task_id)
        return task

    async def reparent_task(self, task_id: UUID, parent_task_id: UUID | None) -> Task:
        task = await self.get(task_id)
        if parent_task_id is None:
            return await self.tasks.reparent(task_id, None)
        if parent_task_id == task_id:
            raise ConflictError("A Task cannot be its own parent")
        parent = await self.tasks.get(parent_task_id)
        if parent is None:
            raise NotFoundError("Parent Task not found")
        if parent.project_id != task.project_id:
            raise ValidationError("Parent Task belongs to a different Project")
        if parent.parent_task_id == task.id:
            raise ConflictError("Task hierarchy cycle detected")
        if parent.is_subtask:
            raise ConflictError("Nested Subtasks are not allowed")
        if await self.tasks.has_children(task_id):
            raise ConflictError("A Task with Subtasks cannot become a Subtask")
        if task.repeat_daily:
            raise ConflictError("A daily recurring task cannot become a Subtask")
        if parent.repeat_daily:
            raise ConflictError("Daily recurring tasks cannot contain subtasks")
        if parent.status == TaskStatus.DONE and task.status != TaskStatus.DONE:
            raise ConflictError("Reopen the parent task before adding a subtask")
        return await self.tasks.reparent(task_id, parent_task_id)

    async def assign_milestone(self, task_id: UUID, milestone_id: UUID | None) -> Task:
        task = await self.get(task_id)
        if task.is_subtask and milestone_id is not None:
            raise ConflictError("Subtasks cannot be assigned directly to a Milestone")
        if milestone_id is not None:
            await self._validate_milestone(task.project_id, milestone_id)
        return await self.tasks.update(task_id, milestone_id=milestone_id)

    async def add_label(self, task_id: UUID, label_id: UUID) -> Task:
        task = await self.get(task_id)
        label = await self.labels.get(label_id)
        if label is None:
            raise NotFoundError("Label not found")
        if label.project_id != task.project_id:
            raise ValidationError("Label belongs to a different Project")
        return await self.tasks.attach_label(task_id, label_id)

    async def remove_label(self, task_id: UUID, label_id: UUID) -> Task:
        await self.get(task_id)
        return await self.tasks.detach_label(task_id, label_id)

    async def _validate_milestone(self, project_id: UUID, milestone_id: UUID) -> None:
        milestone = await self.milestones.get(milestone_id)
        if milestone is None:
            raise NotFoundError("Milestone not found")
        if milestone.project_id != project_id:
            raise ValidationError("Milestone belongs to a different Project")
