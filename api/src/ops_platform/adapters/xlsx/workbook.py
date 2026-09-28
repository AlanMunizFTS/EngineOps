"""Entry point for the project export: a two-sheet .xlsx workbook (Kanban +
Timeline) built from the same domain data the web app renders, so the
snapshot always matches what's on screen at export time."""

from __future__ import annotations

import io
from uuid import UUID

from openpyxl import Workbook

from ops_platform.adapters.xlsx.kanban_sheet import write_kanban_sheet
from ops_platform.adapters.xlsx.timeline_sheet import write_timeline_sheet
from ops_platform.domain.entities import Issue, KanbanBoard, Project


def build_project_export_workbook(
    project: Project,
    issues: list[Issue],
    board: KanbanBoard | None,
    member_names: dict[UUID, str],
) -> bytes:
    workbook = Workbook()
    kanban_sheet = workbook.active
    kanban_sheet.title = "Kanban"
    write_kanban_sheet(kanban_sheet, issues, board, member_names)

    timeline_sheet = workbook.create_sheet("Timeline")
    write_timeline_sheet(timeline_sheet, project.name, issues, member_names)

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
