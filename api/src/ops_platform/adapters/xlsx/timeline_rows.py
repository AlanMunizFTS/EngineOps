"""Depth-first activity ordering for the Timeline sheet: parents immediately
followed by their children, siblings sorted by start date - the same order
the web Schedule view's row tree produces, minus the collapse/expand state
that only makes sense in an interactive UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from ops_platform.domain.entities import Issue


@dataclass(frozen=True, slots=True)
class TimelineRow:
    issue: Issue
    depth: int


def order_timeline_rows(issues: list[Issue]) -> list[TimelineRow]:
    by_id = {issue.id: issue for issue in issues}
    children_by_parent: dict[UUID | None, list[Issue]] = {}
    for issue in issues:
        parent_id = issue.parent_issue_id if issue.parent_issue_id in by_id else None
        children_by_parent.setdefault(parent_id, []).append(issue)
    for siblings in children_by_parent.values():
        siblings.sort(key=lambda i: (i.start_date or date.max, i.title.lower()))

    rows: list[TimelineRow] = []

    def visit(parent_id: UUID | None, depth: int) -> None:
        for issue in children_by_parent.get(parent_id, []):
            rows.append(TimelineRow(issue, depth))
            visit(issue.id, depth + 1)

    visit(None, 0)
    return rows
