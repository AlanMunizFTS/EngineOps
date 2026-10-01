"""Depth-first activity ordering for the Timeline sheet: parents immediately
followed by their children, siblings sorted by start date - the same order
the web Schedule view's row tree produces, minus the collapse/expand state
that only makes sense in an interactive UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from ops_platform.domain.entities import Task


@dataclass(frozen=True, slots=True)
class TimelineRow:
    task: Task
    depth: int


def order_timeline_rows(tasks: list[Task]) -> list[TimelineRow]:
    by_id = {task.id: task for task in tasks}
    children_by_parent: dict[UUID | None, list[Task]] = {}
    for task in tasks:
        parent_id = task.parent_task_id if task.parent_task_id in by_id else None
        children_by_parent.setdefault(parent_id, []).append(task)
    for siblings in children_by_parent.values():
        siblings.sort(key=lambda i: (i.start_date or date.max, i.title.lower()))

    rows: list[TimelineRow] = []

    def visit(parent_id: UUID | None, depth: int) -> None:
        for task in children_by_parent.get(parent_id, []):
            rows.append(TimelineRow(task, depth))
            # The domain permits exactly one child level.
            if depth == 0:
                visit(task.id, 1)

    visit(None, 0)
    return rows
