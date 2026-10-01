from datetime import UTC, date, datetime

from ops_platform.domain.entities import TaskPriority, TaskStatus
from ops_platform.domain.scheduling import (
    ScheduleStatus,
    Urgency,
    calculate_days_planned,
    calculate_priority_score,
    calculate_schedule_status,
    calculate_urgency,
    should_auto_advance_to_todo,
    to_business_date,
    today_in_business_timezone,
    working_days_remaining,
    working_days_taken,
)

# 2026-07-22 is a Wednesday.
_WED = date(2026, 7, 22)
_THU = date(2026, 7, 23)
_FRI = date(2026, 7, 24)
_SAT = date(2026, 7, 25)
_SUN = date(2026, 7, 26)
_MON = date(2026, 7, 27)


def test_working_days_remaining_skips_weekends() -> None:
    assert working_days_remaining(_WED, _WED) == 0
    assert working_days_remaining(_WED, _THU) == 1
    assert working_days_remaining(_WED, _FRI) == 2
    # Sat/Sun must not count: Thu, Fri, Mon = 3 working days.
    assert working_days_remaining(_WED, _MON) == 3


def test_working_days_remaining_overdue_is_zero() -> None:
    assert working_days_remaining(_WED, date(2026, 7, 20)) == 0


def test_calculate_urgency_boundaries() -> None:
    assert calculate_urgency(_WED, _WED) == Urgency.HIGH
    assert calculate_urgency(_WED, _THU) == Urgency.MEDIUM
    assert calculate_urgency(_WED, _FRI) == Urgency.LOW
    assert calculate_urgency(_WED, _MON) == Urgency.LOW
    assert calculate_urgency(_WED, date(2026, 7, 20)) == Urgency.HIGH


def test_calculate_urgency_none_without_due_date() -> None:
    assert calculate_urgency(_WED, None) is None


def test_priority_score_matrix() -> None:
    expected = {
        (Urgency.LOW, TaskPriority.LOW): 1,
        (Urgency.LOW, TaskPriority.MEDIUM): 2,
        (Urgency.LOW, TaskPriority.HIGH): 3,
        (Urgency.MEDIUM, TaskPriority.LOW): 4,
        (Urgency.MEDIUM, TaskPriority.MEDIUM): 5,
        (Urgency.MEDIUM, TaskPriority.HIGH): 6,
        (Urgency.HIGH, TaskPriority.LOW): 7,
        (Urgency.HIGH, TaskPriority.MEDIUM): 8,
        (Urgency.HIGH, TaskPriority.HIGH): 9,
    }
    for (urgency, importance), score in expected.items():
        assert calculate_priority_score(urgency, importance) == score


def test_priority_score_urgent_importance_always_ten() -> None:
    assert calculate_priority_score(Urgency.LOW, TaskPriority.URGENT) == 10
    assert calculate_priority_score(Urgency.HIGH, TaskPriority.URGENT) == 10
    assert calculate_priority_score(None, TaskPriority.URGENT) == 10


def test_priority_score_none_without_urgency_or_urgent() -> None:
    assert calculate_priority_score(None, TaskPriority.HIGH) is None


def test_priority_score_overdue_always_ten_regardless_of_importance() -> None:
    assert calculate_priority_score(Urgency.HIGH, TaskPriority.LOW, is_overdue=True) == 10
    assert calculate_priority_score(Urgency.HIGH, TaskPriority.MEDIUM, is_overdue=True) == 10
    assert calculate_priority_score(Urgency.HIGH, TaskPriority.HIGH, is_overdue=True) == 10


def test_priority_score_not_overdue_uses_normal_matrix() -> None:
    assert calculate_priority_score(Urgency.HIGH, TaskPriority.LOW, is_overdue=False) == 7


def test_priority_score_zero_when_not_started_overrides_everything() -> None:
    assert calculate_priority_score(Urgency.HIGH, TaskPriority.URGENT, has_started=False) == 0
    assert (
        calculate_priority_score(
            Urgency.HIGH, TaskPriority.LOW, is_overdue=True, has_started=False
        )
        == 0
    )
    assert calculate_priority_score(None, TaskPriority.URGENT, has_started=False) == 0


def test_working_days_taken() -> None:
    assert working_days_taken(_WED, _WED) == 0
    assert working_days_taken(_WED, _THU) == 1
    assert working_days_taken(_WED, _MON) == 3


def test_calculate_days_planned_inclusive_both_ends() -> None:
    # Same-day weekday task: 1 day planned, not 0.
    assert calculate_days_planned(_WED, _WED) == 1
    # Wed through Fri: 3 working days, inclusive.
    assert calculate_days_planned(_WED, _FRI) == 3
    # Wed through Mon: Wed,Thu,Fri,Mon = 4 (Sat/Sun excluded).
    assert calculate_days_planned(_WED, _MON) == 4


def test_calculate_days_planned_none_cases() -> None:
    assert calculate_days_planned(None, _WED) is None
    assert calculate_days_planned(_WED, None) is None
    assert calculate_days_planned(_FRI, _WED) is None  # due before start


def test_schedule_status() -> None:
    assert calculate_schedule_status(_WED, _WED, _WED) == ScheduleStatus.CLOSED
    assert calculate_schedule_status(_WED, _THU, None) == ScheduleStatus.ON_TIME
    assert calculate_schedule_status(_WED, date(2026, 7, 20), None) == ScheduleStatus.LATE
    assert calculate_schedule_status(_WED, None, None) is None


def test_today_in_business_timezone_is_fixed_utc_minus_6() -> None:
    # 05:59 UTC is still 23:59 the *previous* day at UTC-6.
    just_before_midnight_utc6 = datetime(2026, 7, 23, 5, 59, tzinfo=UTC)
    just_after_midnight_utc6 = datetime(2026, 7, 23, 6, 0, tzinfo=UTC)
    assert to_business_date(just_before_midnight_utc6) == date(2026, 7, 22)
    assert to_business_date(just_after_midnight_utc6) == date(2026, 7, 23)


def test_should_auto_advance_to_todo_when_start_date_arrives() -> None:
    assert should_auto_advance_to_todo(_WED, TaskStatus.BACKLOG, _WED) is True
    assert should_auto_advance_to_todo(_WED, TaskStatus.BACKLOG, date(2026, 7, 20)) is True


def test_should_not_auto_advance_before_start_date() -> None:
    assert should_auto_advance_to_todo(_WED, TaskStatus.BACKLOG, _THU) is False


def test_should_not_auto_advance_without_start_date() -> None:
    assert should_auto_advance_to_todo(_WED, TaskStatus.BACKLOG, None) is False


def test_should_not_auto_advance_tasks_already_moved_out_of_backlog() -> None:
    assert should_auto_advance_to_todo(_WED, TaskStatus.TODO, _WED) is False
    assert should_auto_advance_to_todo(_WED, TaskStatus.IN_PROGRESS, _WED) is False
    assert should_auto_advance_to_todo(_WED, TaskStatus.DONE, _WED) is False


def test_today_in_business_timezone_ignores_host_local_clock() -> None:
    # Doesn't crash / returns a plain date regardless of the host's own
    # timezone setting - the point of the fixed offset is not depending on it.
    assert isinstance(today_in_business_timezone(), date)
