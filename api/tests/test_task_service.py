import uuid
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from ops_platform.application.errors import ConflictError, NotFoundError, ValidationError
from ops_platform.application.task_service import TaskService
from ops_platform.domain.entities import (
    Label,
    Milestone,
    MilestoneStatus,
    Task,
    TaskPriority,
    TaskStatus,
    TaskType,
)


class MemoryTasks:
    def __init__(self) -> None:
        self.values: dict[uuid.UUID, Task] = {}

    async def create(self, **values):
        now = datetime.now(UTC)
        task = Task(
            id=uuid.uuid4(),
            status=TaskStatus.BACKLOG,
            created_at=now,
            updated_at=now,
            closed_at=None,
            labels=[],
            **values,
        )
        self.values[task.id] = task
        return task

    async def get(self, task_id):
        task = self.values.get(task_id)
        if task is None:
            return None
        children = await self.list_subtasks(task_id)
        return replace(
            task,
            subtasks_total=len(children),
            subtasks_completed=sum(c.status == TaskStatus.DONE for c in children),
        )

    async def list_subtasks(self, task_id):
        return [task for task in self.values.values() if task.parent_task_id == task_id]

    async def has_children(self, task_id):
        return bool(await self.list_subtasks(task_id))

    async def update(self, task_id, **changes):
        task = replace(self.values[task_id], **changes, updated_at=datetime.now(UTC))
        self.values[task_id] = task
        return task

    async def set_status(self, task_id, status):
        task = replace(
            self.values[task_id],
            status=status,
            closed_at=datetime.now(UTC) if status == TaskStatus.DONE else None,
        )
        self.values[task_id] = task
        return task

    async def reparent(self, task_id, parent_task_id):
        task = replace(
            self.values[task_id],
            parent_task_id=parent_task_id,
            milestone_id=None,
            parent_assigned_at=datetime.now(UTC) if parent_task_id else None,
        )
        self.values[task_id] = task
        return task

    async def delete(self, task_id):
        del self.values[task_id]

    async def attach_label(self, task_id, label_id):
        return self.values[task_id]

    async def detach_label(self, task_id, label_id):
        return self.values[task_id]


class MemoryMilestones:
    def __init__(self) -> None:
        self.values: dict[uuid.UUID, Milestone] = {}

    async def get(self, milestone_id):
        return self.values.get(milestone_id)


class MemoryLabels:
    def __init__(self) -> None:
        self.values: dict[uuid.UUID, Label] = {}

    async def get(self, label_id):
        return self.values.get(label_id)


@pytest.fixture
def context():
    tasks = MemoryTasks()
    milestones = MemoryMilestones()
    labels = MemoryLabels()
    return tasks, milestones, labels, TaskService(tasks, milestones, labels)


async def create_task(service, project_id, title="Task"):
    return await service.create_task(
        project_id=project_id,
        title=title,
        task_type=TaskType.TASK,
        priority=TaskPriority.MEDIUM,
    )


@pytest.mark.asyncio
async def test_rejects_nested_and_cross_project_subtasks(context):
    _, _, _, service = context
    project_a, project_b = uuid.uuid4(), uuid.uuid4()
    parent = await create_task(service, project_a)
    child = await service.create_subtask(parent.id, project_id=project_a, title="Child")

    with pytest.raises(ConflictError, match="Nested"):
        await service.create_subtask(child.id, project_id=project_a, title="Too deep")
    with pytest.raises(ValidationError, match="different Project"):
        await service.create_subtask(parent.id, project_id=project_b, title="Wrong project")


@pytest.mark.asyncio
async def test_completion_requires_all_subtasks_done(context):
    _, _, _, service = context
    project_id = uuid.uuid4()
    parent = await create_task(service, project_id)
    child = await service.create_subtask(parent.id, project_id=project_id, title="Child")

    with pytest.raises(ConflictError, match="subtasks remain incomplete"):
        await service.change_status(parent.id, TaskStatus.DONE)
    await service.change_status(child.id, TaskStatus.DONE)
    completed = await service.change_status(parent.id, TaskStatus.DONE)
    assert completed.status == TaskStatus.DONE

    with pytest.raises(ConflictError, match="Parent task must be reopened"):
        await service.change_status(child.id, TaskStatus.IN_PROGRESS)


@pytest.mark.asyncio
async def test_done_parent_rejects_new_subtask(context):
    _, _, _, service = context
    project_id = uuid.uuid4()
    parent = await create_task(service, project_id)
    await service.change_status(parent.id, TaskStatus.DONE)
    with pytest.raises(ConflictError, match="Reopen"):
        await service.create_subtask(parent.id, project_id=project_id, title="Late child")


@pytest.mark.asyncio
async def test_parent_with_children_cannot_be_reparented_or_deleted(context):
    _, _, _, service = context
    project_id = uuid.uuid4()
    parent = await create_task(service, project_id, "Parent")
    target = await create_task(service, project_id, "Target")
    await service.create_subtask(parent.id, project_id=project_id, title="Child")

    with pytest.raises(ConflictError, match="cannot become a Subtask"):
        await service.reparent_task(parent.id, target.id)
    with pytest.raises(ConflictError, match="contains subtasks"):
        await service.delete_task(parent.id)


@pytest.mark.asyncio
async def test_subtask_cannot_store_milestone(context):
    _, milestones, _, service = context
    project_id = uuid.uuid4()
    now = datetime.now(UTC)
    milestone = Milestone(
        id=uuid.uuid4(),
        project_id=project_id,
        title="M1",
        description=None,
        status=MilestoneStatus.OPEN,
        due_date=None,
        created_at=now,
        updated_at=now,
    )
    milestones.values[milestone.id] = milestone
    parent = await create_task(service, project_id)
    child = await service.create_subtask(parent.id, project_id=project_id, title="Child")

    with pytest.raises(ConflictError, match="Subtasks cannot"):
        await service.assign_milestone(child.id, milestone.id)
    assigned = await service.assign_milestone(parent.id, milestone.id)
    assert assigned.milestone_id == milestone.id


@pytest.mark.asyncio
async def test_parent_must_exist_and_self_parent_is_rejected(context):
    _, _, _, service = context
    project_id = uuid.uuid4()
    task = await create_task(service, project_id)

    with pytest.raises(NotFoundError, match="Parent Task not found"):
        await service.create_subtask(uuid.uuid4(), project_id=project_id, title="Orphan")
    with pytest.raises(ConflictError, match="own parent"):
        await service.reparent_task(task.id, task.id)


@pytest.mark.asyncio
async def test_promote_and_reparent_subtask(context):
    _, _, _, service = context
    project_id = uuid.uuid4()
    first_parent = await create_task(service, project_id, "First")
    second_parent = await create_task(service, project_id, "Second")
    child = await service.create_subtask(first_parent.id, project_id=project_id, title="Movable")

    moved = await service.reparent_task(child.id, second_parent.id)
    assert moved.parent_task_id == second_parent.id
    assert moved.parent_assigned_at is not None

    promoted = await service.reparent_task(child.id, None)
    assert promoted.parent_task_id is None
    assert promoted.parent_assigned_at is None
    assert promoted.milestone_id is None


@pytest.mark.asyncio
async def test_rejects_two_task_cycle(context):
    tasks, _, _, service = context
    project_id = uuid.uuid4()
    first = await create_task(service, project_id, "First")
    second = await create_task(service, project_id, "Second")
    tasks.values[first.id] = replace(first, parent_task_id=second.id)

    with pytest.raises(ConflictError, match="cycle"):
        await service.reparent_task(second.id, first.id)


@pytest.mark.asyncio
async def test_milestone_must_belong_to_same_project(context):
    _, milestones, _, service = context
    task_project = uuid.uuid4()
    now = datetime.now(UTC)
    milestone = Milestone(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        title="Other project",
        description=None,
        status=MilestoneStatus.OPEN,
        due_date=None,
        created_at=now,
        updated_at=now,
    )
    milestones.values[milestone.id] = milestone
    task = await create_task(service, task_project)

    with pytest.raises(ValidationError, match="different Project"):
        await service.assign_milestone(task.id, milestone.id)
