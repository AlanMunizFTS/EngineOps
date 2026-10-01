"""Pure, side-effect-free scheduling calculations for the project Schedule
(Gantt) view: working-day arithmetic, Urgency, and the composite Priority
Score. No I/O, no ports needed - these are deterministic functions of
(today, due_date, ...) inputs, always recomputed at request time rather than
stored, since "days remaining" is only ever correct as of the moment it's read.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum

from ops_platform.domain.entities import TaskPriority, TaskStatus

_WEEKEND = (5, 6)  # date.weekday(): Saturday=5, Sunday=6

# Fixed UTC-6 (Mexico Central Time, no DST) - the one calendar "today" every
# schedule calculation uses, deliberately NOT the host/container's local
# clock (Docker images default to UTC; a dev host's local zone is whatever
# it happens to be) - both are unreliable and can silently disagree with
# each other, which is what caused a real off-by-one in schedule/urgency
# math depending on what machine and time of day a request landed at.
_BUSINESS_UTC_OFFSET = timedelta(hours=-6)


def today_in_business_timezone() -> date:
    """ "Today" for schedule/urgency purposes, always UTC-6 regardless of
    where the server process happens to be running or what its system
    clock's local timezone is set to."""
    return (datetime.now(UTC) + _BUSINESS_UTC_OFFSET).date()


def to_business_date(moment: datetime) -> date:
    """Converts an absolute timestamp (e.g. `closed_at`, stored in UTC) to
    its calendar date in the fixed UTC-6 business timezone - not the UTC
    calendar date, which can already be a day ahead during the business
    timezone's afternoon/evening."""
    return (moment.astimezone(UTC) + _BUSINESS_UTC_OFFSET).date()


def _working_days_after(start: date, end: date) -> int:
    """Working days (Mon-Fri) strictly after `start` up to and including
    `end`. 0 if `end <= start`."""
    if end <= start:
        return 0
    count = 0
    current = start
    while current < end:
        current += timedelta(days=1)
        if current.weekday() not in _WEEKEND:
            count += 1
    return count


class Urgency(StrEnum):
    """Time-pressure signal derived from working days left until `due_date` -
    recomputed daily, unlike `TaskPriority` (called "Importance" in this
    context), which a person assigns and which doesn't drift with the
    calendar. 0 working days left (due today or overdue) -> HIGH; 1 -> MEDIUM;
    2+ -> LOW."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def working_days_remaining(today: date, due_date: date) -> int:
    """Working days strictly after `today` up to and including `due_date`.
    0 if `due_date` is today or already past (overdue)."""
    return _working_days_after(today, due_date)


def calculate_urgency(today: date, due_date: date | None) -> Urgency | None:
    if due_date is None:
        return None
    remaining = working_days_remaining(today, due_date)
    if remaining == 0:
        return Urgency.HIGH
    if remaining == 1:
        return Urgency.MEDIUM
    return Urgency.LOW


def working_days_taken(start_date: date, reference_date: date) -> int:
    """Working days elapsed from `start_date` up to `reference_date` (today,
    if still open, or the close date). 0 if the task starts today or in the
    future."""
    return _working_days_after(start_date, reference_date)


def calculate_days_planned(start_date: date | None, due_date: date | None) -> int | None:
    """Budgeted duration in working days, both endpoints inclusive - a task
    starting and due the same weekday is "1 day planned", not 0. Computed
    from `start_date`/`due_date` rather than stored, so it can never drift
    out of sync with them (see docs/architecture/adr/0011)."""
    if start_date is None or due_date is None or due_date < start_date:
        return None
    count = 0
    current = start_date
    while current <= due_date:
        if current.weekday() not in _WEEKEND:
            count += 1
        current += timedelta(days=1)
    return count


_URGENCY_RANK: dict[Urgency, int] = {Urgency.LOW: 0, Urgency.MEDIUM: 1, Urgency.HIGH: 2}
_IMPORTANCE_RANK: dict[TaskPriority, int] = {
    TaskPriority.LOW: 1,
    TaskPriority.MEDIUM: 2,
    TaskPriority.HIGH: 3,
}


def calculate_priority_score(
    urgency: Urgency | None,
    importance: TaskPriority,
    *,
    is_overdue: bool = False,
    has_started: bool = True,
) -> int | None:
    """1-10 composite of Urgency (time-pressure) and Importance (assigned
    severity). `has_started=False` (a `start_date` set in the future - the
    activity isn't due to begin yet) always scores 0, overriding every other
    signal: an activity nobody should be working on yet doesn't need to
    compete for attention on the board no matter how close its due date is.
    Otherwise, Importance=URGENT always scores 10, overriding urgency; an
    overdue due_date (still open, past due) also always scores 10 regardless
    of importance - a late task needs attention today no matter how it was
    triaged. Otherwise score = urgency_rank * 3 + importance_rank, covering
    1-9 across the Low/Medium/High (urgency) x Low/Medium/High (importance)
    grid. `None` only when urgency can't be computed (no due_date) and
    importance isn't URGENT - there's nothing to score against."""
    if not has_started:
        return 0
    if importance == TaskPriority.URGENT or is_overdue:
        return 10
    if urgency is None:
        return None
    return _URGENCY_RANK[urgency] * 3 + _IMPORTANCE_RANK[importance]


def should_auto_advance_to_todo(today: date, status: TaskStatus, start_date: date | None) -> bool:
    """A task an operator parked in Backlog because it wasn't time to start
    it yet should surface in ToDo the day its `start_date` arrives, with no
    one needing to remember to drag it over manually. Only ever moves
    Backlog -> ToDo: a task a person has already moved anywhere else
    (ToDo, In Progress, ...) is left alone, and one with no `start_date` has
    no signal to advance on, so it stays in Backlog until manually moved."""
    return status == TaskStatus.BACKLOG and start_date is not None and start_date <= today


class ScheduleStatus(StrEnum):
    """Schedule adherence, distinct from `TaskStatus` (the kanban workflow
    state) - this is purely "are we going to make the due date"."""

    CLOSED = "closed"
    ON_TIME = "on_time"
    LATE = "late"


def calculate_schedule_status(
    today: date, due_date: date | None, closed_at_date: date | None
) -> ScheduleStatus | None:
    if closed_at_date is not None:
        return ScheduleStatus.CLOSED
    if due_date is None:
        return None
    return ScheduleStatus.LATE if due_date < today else ScheduleStatus.ON_TIME


class BarSegmentKind(StrEnum):
    """Presentation-agnostic classification of a Gantt bar segment - callers
    (web Schedule view, Excel export) each map these to their own color
    scheme rather than the domain owning a color string."""

    ON_TRACK = "on_track"
    LATE = "late"
    EARLY_BUFFER = "early_buffer"


@dataclass(frozen=True, slots=True)
class BarSegment:
    start: date
    end: date
    kind: BarSegmentKind


def compute_bar_segments(
    today: date,
    start_date: date | None,
    due_date: date | None,
    closed_at_date: date | None,
    schedule_status: ScheduleStatus | None,
) -> list[BarSegment]:
    """Mirrors the web Schedule view's `computeBarSegments` (SchedulePage.tsx)
    exactly, so the Gantt bar in the Excel export matches what's on screen.
    An open (not yet closed) activity gets one segment: red and stretching to
    `today` if it's overdue (so the bar keeps growing day by day instead of
    stopping at `due_date`), blue otherwise. A closed activity compares its
    close date to its due date: closed on/before due -> blue up to the close
    date, plus a green "finished early" buffer segment out to due_date if it
    closed before then; closed after due -> blue up to due_date then red from
    due_date to the close date."""
    if due_date is None:
        return []
    start = start_date or due_date

    if closed_at_date is None:
        is_late = schedule_status == ScheduleStatus.LATE
        end = today if (is_late and today > due_date) else due_date
        kind = BarSegmentKind.LATE if is_late else BarSegmentKind.ON_TRACK
        return [BarSegment(start, end, kind)]

    if closed_at_date <= due_date:
        segments = [BarSegment(start, closed_at_date, BarSegmentKind.ON_TRACK)]
        if closed_at_date < due_date:
            segments.append(
                BarSegment(
                    closed_at_date + timedelta(days=1), due_date, BarSegmentKind.EARLY_BUFFER
                )
            )
        return segments

    return [
        BarSegment(start, due_date, BarSegmentKind.ON_TRACK),
        BarSegment(due_date + timedelta(days=1), closed_at_date, BarSegmentKind.LATE),
    ]
