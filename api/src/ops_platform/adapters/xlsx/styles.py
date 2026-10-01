"""Shared cell styling for the project export workbook - colors chosen to
match the web app's own palette (TaskBadges.tsx PRIORITY_COLORS / the
Schedule Gantt bar colors in SchedulePage.tsx) so the Excel export looks like
a snapshot of the app, not a different color scheme."""

from __future__ import annotations

from openpyxl.styles import Alignment, Font, PatternFill

from ops_platform.domain.scheduling import BarSegmentKind

HEADER_FILL = PatternFill("solid", fgColor="1E3A5F")
HEADER_FONT = Font(color="FFFFFF", bold=True)
HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center")

TODAY_FILL = PatternFill("solid", fgColor="FFE68A")
WEEKEND_FILL = PatternFill("solid", fgColor="F1F5F9")

PRIORITY_FILLS: dict[str, str] = {
    "low": "94A3B8",  # slate-400
    "medium": "38BDF8",  # sky-400
    "high": "F59E0B",  # amber-500
    "urgent": "EF4444",  # red-500
}

SEGMENT_FILLS: dict[BarSegmentKind, PatternFill] = {
    BarSegmentKind.ON_TRACK: PatternFill("solid", fgColor="38BDF8"),  # bg-sky-500
    BarSegmentKind.LATE: PatternFill("solid", fgColor="EF4444"),  # bg-red-500
    BarSegmentKind.EARLY_BUFFER: PatternFill("solid", fgColor="10B981"),  # bg-emerald-500
}


def style_header_row(ws, row: int, first_col: int, last_col: int) -> None:
    for col in range(first_col, last_col + 1):
        cell = ws.cell(row=row, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = HEADER_ALIGNMENT
