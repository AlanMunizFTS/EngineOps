import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient

from ops_platform.api.routers.tasks import task_response
from ops_platform.domain.entities import Task, TaskPriority, TaskStatus, TaskType


def _create_project(client: TestClient, auth_headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Endforms"}, headers=auth_headers)
    return response.json()["id"]


def test_task_response_closed_at_date_uses_business_timezone_not_utc() -> None:
    # 19:00 on the 23rd at UTC-6 is already 01:00 on the 24th in UTC - the
    # closed_at_date shown to the user must track the former, not the raw
    # UTC calendar day closed_at happens to serialize under.
    task = Task(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        title="Late shift close",
        description=None,
        status=TaskStatus.DONE,
        priority=TaskPriority.MEDIUM,
        task_type=TaskType.TASK,
        assignee_id=None,
        created_by=None,
        created_at=datetime(2026, 7, 23, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 7, 23, 12, 0, tzinfo=UTC),
        closed_at=datetime(2026, 7, 24, 1, 0, tzinfo=UTC),
    )

    response = task_response(task)

    assert response.closed_at is not None
    assert response.closed_at.date() == date(2026, 7, 24)
    assert response.closed_at_date == date(2026, 7, 23)


def test_create_task_defaults_to_backlog(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)

    response = client.post(
        f"/projects/{project_id}/tasks", json={"title": "Fix conveyor jam"}, headers=auth_headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["project_id"] == project_id
    assert body["status"] == "backlog"
    assert body["priority"] == "medium"
    assert body["task_type"] == "task"
    assert body["labels"] == []


def test_task_supports_multiple_assignees(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    assignee_ids = [uuid.uuid4(), uuid.uuid4()]

    created = client.post(
        f"/projects/{project_id}/tasks",
        json={"title": "Joint inspection", "assignee_ids": [str(item) for item in assignee_ids]},
        headers=auth_headers,
    )

    assert created.status_code == 201
    body = created.json()
    assert body["assignee_ids"] == [str(item) for item in assignee_ids]
    assert body["assignee_id"] == str(assignee_ids[0])

    replacement = uuid.uuid4()
    updated = client.patch(
        f"/tasks/{body['id']}",
        json={"assignee_id": str(replacement)},
        headers=auth_headers,
    ).json()
    assert updated["assignee_ids"] == [str(replacement), str(assignee_ids[1])]

    filtered = client.get(
        f"/projects/{project_id}/tasks",
        params={"assignee_id": str(assignee_ids[1])},
        headers=auth_headers,
    )
    assert [task["id"] for task in filtered.json()] == [body["id"]]


def test_create_task_records_audit_entry(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    client.post(
        f"/projects/{project_id}/tasks", json={"title": "Fix conveyor jam"}, headers=auth_headers
    )

    timeline = client.get(f"/projects/{project_id}/timeline", headers=auth_headers).json()
    assert any(entry["action"] == "task.created" for entry in timeline)


def test_list_project_tasks_filters_by_status(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    open_task = client.post(
        f"/projects/{project_id}/tasks", json={"title": "Open task"}, headers=auth_headers
    ).json()
    done_task = client.post(
        f"/projects/{project_id}/tasks", json={"title": "Done task"}, headers=auth_headers
    ).json()
    client.patch(f"/tasks/{done_task['id']}/status", json={"status": "done"}, headers=auth_headers)

    backlog_tasks = client.get(
        f"/projects/{project_id}/tasks", params={"status": "backlog"}, headers=auth_headers
    ).json()
    assert {i["id"] for i in backlog_tasks} == {open_task["id"]}

    done_tasks = client.get(
        f"/projects/{project_id}/tasks", params={"status": "done"}, headers=auth_headers
    ).json()
    assert {i["id"] for i in done_tasks} == {done_task["id"]}


def test_list_project_tasks_auto_advances_backlog_to_todo_on_start_date(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    today = date.today().isoformat()
    due = client.post(
        f"/projects/{project_id}/tasks",
        json={"title": "Starts today", "start_date": today},
        headers=auth_headers,
    ).json()
    assert due["status"] == "backlog"

    tasks = client.get(f"/projects/{project_id}/tasks", headers=auth_headers).json()
    advanced = next(i for i in tasks if i["id"] == due["id"])
    assert advanced["status"] == "todo"


def test_list_project_tasks_leaves_future_start_dates_in_backlog(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    far_future = (date.today() + timedelta(days=30)).isoformat()
    task = client.post(
        f"/projects/{project_id}/tasks",
        json={"title": "Not yet", "start_date": far_future},
        headers=auth_headers,
    ).json()

    tasks = client.get(f"/projects/{project_id}/tasks", headers=auth_headers).json()
    unchanged = next(i for i in tasks if i["id"] == task["id"])
    assert unchanged["status"] == "backlog"


def test_list_project_tasks_does_not_auto_advance_tasks_moved_out_of_backlog(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    today = date.today().isoformat()
    task = client.post(
        f"/projects/{project_id}/tasks",
        json={"title": "Manually moved", "start_date": today},
        headers=auth_headers,
    ).json()
    client.patch(
        f"/tasks/{task['id']}/status", json={"status": "in_progress"}, headers=auth_headers
    )

    tasks = client.get(f"/projects/{project_id}/tasks", headers=auth_headers).json()
    unchanged = next(i for i in tasks if i["id"] == task["id"])
    assert unchanged["status"] == "in_progress"


def test_update_task_status_sets_and_clears_closed_at(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    task = client.post(
        f"/projects/{project_id}/tasks", json={"title": "Fix conveyor jam"}, headers=auth_headers
    ).json()
    assert task["closed_at"] is None

    closed = client.patch(
        f"/tasks/{task['id']}/status", json={"status": "done"}, headers=auth_headers
    ).json()
    assert closed["closed_at"] is not None

    reopened = client.patch(
        f"/tasks/{task['id']}/status", json={"status": "todo"}, headers=auth_headers
    ).json()
    assert reopened["closed_at"] is None


def test_attach_and_detach_label(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    task = client.post(
        f"/projects/{project_id}/tasks", json={"title": "Fix conveyor jam"}, headers=auth_headers
    ).json()
    label = client.post(
        f"/projects/{project_id}/labels",
        json={"name": "bug", "color": "#ff0000"},
        headers=auth_headers,
    ).json()

    attached = client.post(
        f"/tasks/{task['id']}/labels/{label['id']}", headers=auth_headers
    ).json()
    assert [label_out["id"] for label_out in attached["labels"]] == [label["id"]]

    filtered = client.get(
        f"/projects/{project_id}/tasks", params={"label_id": label["id"]}, headers=auth_headers
    ).json()
    assert {i["id"] for i in filtered} == {task["id"]}

    detached = client.delete(
        f"/tasks/{task['id']}/labels/{label['id']}", headers=auth_headers
    ).json()
    assert detached["labels"] == []


def test_update_task(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    task = client.post(
        f"/projects/{project_id}/tasks", json={"title": "Fix conveyor jam"}, headers=auth_headers
    ).json()

    response = client.patch(
        f"/tasks/{task['id']}",
        json={
            "title": "Fix conveyor jam - urgent",
            "description": "Line 4 is down",
            "task_type": "bug",
            "priority": "urgent",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Fix conveyor jam - urgent"
    assert body["priority"] == "urgent"
    assert body["task_type"] == "bug"


def test_get_task_404_for_unknown_id(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get(f"/tasks/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_create_task_without_schedule_fields_has_null_computed_fields(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)

    task = client.post(
        f"/projects/{project_id}/tasks", json={"title": "No schedule"}, headers=auth_headers
    ).json()
    assert task["parent_task_id"] is None
    assert task["start_date"] is None
    assert task["due_date"] is None
    assert task["days_planned"] is None
    assert task["days_taken"] is None
    assert task["urgency"] is None
    assert task["priority_score"] is None
    assert task["schedule_status"] is None


def test_create_task_with_schedule_fields(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    today = date.today()

    task = client.post(
        f"/projects/{project_id}/tasks",
        json={
            "title": "Wrinkle",
            "start_date": today.isoformat(),
            "due_date": today.isoformat(),
        },
        headers=auth_headers,
    ).json()
    assert task["start_date"] == today.isoformat()
    assert task["due_date"] == today.isoformat()
    # Same-day span, both endpoints inclusive -> 1 working day planned
    # (unless today happens to be a weekend, in which case 0).
    assert task["days_planned"] in (0, 1)
    # Due today -> 0 working days remaining -> High urgency.
    assert task["urgency"] == "high"
    assert task["schedule_status"] == "on_time"
    # Importance defaults to medium; High urgency x Medium importance = 8.
    assert task["priority_score"] == 8


def test_task_urgency_low_for_far_future_due_date(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    far_future = (date.today() + timedelta(days=30)).isoformat()

    task = client.post(
        f"/projects/{project_id}/tasks",
        json={"title": "Split", "due_date": far_future, "priority": "low"},
        headers=auth_headers,
    ).json()
    assert task["urgency"] == "low"
    # Low urgency x Low importance = 1.
    assert task["priority_score"] == 1


def test_task_priority_score_is_ten_when_importance_is_urgent_regardless_of_urgency(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    far_future = (date.today() + timedelta(days=30)).isoformat()

    task = client.post(
        f"/projects/{project_id}/tasks",
        json={"title": "Breakage", "due_date": far_future, "priority": "urgent"},
        headers=auth_headers,
    ).json()
    assert task["urgency"] == "low"
    assert task["priority_score"] == 10


def test_task_schedule_status_late_when_overdue_and_open(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    overdue = (date.today() - timedelta(days=10)).isoformat()

    task = client.post(
        f"/projects/{project_id}/tasks",
        json={"title": "Edge", "due_date": overdue},
        headers=auth_headers,
    ).json()
    assert task["schedule_status"] == "late"
    assert task["urgency"] == "high"
    # Overdue always scores 10, regardless of importance (default: medium).
    assert task["priority_score"] == 10


def test_task_priority_score_zero_when_start_date_in_future(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    due_today = date.today().isoformat()

    task = client.post(
        f"/projects/{project_id}/tasks",
        json={
            "title": "Not due to start yet",
            "start_date": tomorrow,
            "due_date": due_today,
            "priority": "urgent",
        },
        headers=auth_headers,
    ).json()
    # Due today + urgent importance would normally score 10, but the
    # activity isn't due to start until tomorrow - score is forced to 0.
    assert task["priority_score"] == 0


def test_task_priority_score_normal_when_due_today_not_overdue(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    today = date.today().isoformat()

    task = client.post(
        f"/projects/{project_id}/tasks",
        json={"title": "Due today", "due_date": today, "priority": "low"},
        headers=auth_headers,
    ).json()
    assert task["schedule_status"] == "on_time"
    assert task["urgency"] == "high"
    # Due today (not overdue) still uses the normal matrix: HIGH urgency x
    # LOW importance = 2*3 + 1 = 7, not the overdue override of 10.
    assert task["priority_score"] == 7


def test_task_schedule_status_closed_after_done(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    today = date.today()
    task = client.post(
        f"/projects/{project_id}/tasks",
        json={"title": "Nylon", "start_date": today.isoformat(), "due_date": today.isoformat()},
        headers=auth_headers,
    ).json()

    closed = client.patch(
        f"/tasks/{task['id']}/status", json={"status": "done"}, headers=auth_headers
    ).json()
    assert closed["schedule_status"] == "closed"
    assert closed["days_taken"] == 0


def test_update_task_preserves_schedule_fields(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    today = date.today().isoformat()
    task = client.post(
        f"/projects/{project_id}/tasks",
        json={"title": "Streaked", "start_date": today, "due_date": today},
        headers=auth_headers,
    ).json()

    updated = client.patch(
        f"/tasks/{task['id']}",
        json={
            "title": "Streaked",
            "task_type": "task",
            "priority": "medium",
            "start_date": today,
            "due_date": today,
        },
        headers=auth_headers,
    ).json()
    assert updated["start_date"] == today
    assert updated["due_date"] == today


def test_task_can_have_a_parent(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    parent = client.post(
        f"/projects/{project_id}/tasks",
        json={"title": "Mushroom Validation"},
        headers=auth_headers,
    ).json()

    child = client.post(
        f"/tasks/{parent['id']}/subtasks",
        json={"title": "Wrinkle"},
        headers=auth_headers,
    ).json()
    assert child["parent_task_id"] == parent["id"]

    reparented = client.patch(
        f"/tasks/{child['id']}/parent",
        json={"parent_task_id": None},
        headers=auth_headers,
    ).json()
    assert reparented["parent_task_id"] is None


def _set_parent(
    client: TestClient, auth_headers: dict[str, str], task: dict, parent_id: str | None
) -> dict:
    return client.patch(
        f"/tasks/{task['id']}/parent",
        json={"parent_task_id": parent_id},
        headers=auth_headers,
    ).json()


def test_relinking_a_parent_bumps_parent_assigned_at(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Reproduces the reported bug: unlink task A from a parent, link B in
    the meantime, then re-link A - A's parent_assigned_at should now be
    *after* B's, so the Schedule view (which sorts siblings by
    parent_assigned_at, not created_at) numbers B before A even though A
    was created first."""
    project_id = _create_project(client, auth_headers)
    parent = client.post(
        f"/projects/{project_id}/tasks", json={"title": "Parent"}, headers=auth_headers
    ).json()
    task_a = client.post(
        f"/tasks/{parent['id']}/subtasks",
        json={"title": "A"},
        headers=auth_headers,
    ).json()
    assert task_a["parent_assigned_at"] is not None

    unlinked = _set_parent(client, auth_headers, task_a, None)
    assert unlinked["parent_assigned_at"] is None

    task_b = client.post(
        f"/tasks/{parent['id']}/subtasks",
        json={"title": "B"},
        headers=auth_headers,
    ).json()

    relinked_a = _set_parent(client, auth_headers, task_a, parent["id"])
    assert relinked_a["parent_assigned_at"] is not None
    assert relinked_a["parent_assigned_at"] > task_b["parent_assigned_at"]


def test_task_history_tracks_status_transitions(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    task = client.post(
        f"/projects/{project_id}/tasks", json={"title": "Fix conveyor jam"}, headers=auth_headers
    ).json()

    client.patch(f"/tasks/{task['id']}/status", json={"status": "todo"}, headers=auth_headers)
    client.patch(
        f"/tasks/{task['id']}/status", json={"status": "in_progress"}, headers=auth_headers
    )
    client.patch(f"/tasks/{task['id']}/status", json={"status": "done"}, headers=auth_headers)

    history = client.get(f"/tasks/{task['id']}/history", headers=auth_headers).json()
    status_changes = [e for e in history if e["action"] == "task.status_changed"]
    assert [e["diff"]["new_status"] for e in status_changes] == [
        "todo",
        "in_progress",
        "done",
    ]
    assert all(e["entity_id"] == task["id"] for e in history)


def test_my_pending_tasks_span_projects_and_only_include_current_user(
    client: TestClient,
    auth_headers: dict[str, str],
    current_user,
) -> None:
    first_project_id = _create_project(client, auth_headers)
    second_project_id = _create_project(client, auth_headers)

    first = client.post(
        f"/projects/{first_project_id}/tasks",
        json={"title": "First assigned task", "assignee_id": str(current_user.id)},
        headers=auth_headers,
    ).json()
    second = client.post(
        f"/projects/{second_project_id}/tasks",
        json={"title": "Second assigned task", "assignee_id": str(current_user.id)},
        headers=auth_headers,
    ).json()
    client.post(
        f"/projects/{first_project_id}/tasks",
        json={"title": "Unassigned task"},
        headers=auth_headers,
    )
    completed = client.post(
        f"/projects/{second_project_id}/tasks",
        json={"title": "Completed task", "assignee_id": str(current_user.id)},
        headers=auth_headers,
    ).json()
    client.patch(
        f"/tasks/{completed['id']}/status",
        json={"status": "done"},
        headers=auth_headers,
    )

    response = client.get("/tasks/assigned-to-me", headers=auth_headers)

    assert response.status_code == 200
    assert {task["id"] for task in response.json()} == {first["id"], second["id"]}


def test_my_pending_tasks_requires_authentication(client: TestClient) -> None:
    assert client.get("/tasks/assigned-to-me").status_code == 401


def test_task_history_404_for_unknown_task(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get(f"/tasks/{uuid.uuid4()}/history", headers=auth_headers)
    assert response.status_code == 404


def test_priority_score_is_none_once_task_is_done(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    far_future = (date.today() + timedelta(days=30)).isoformat()
    task = client.post(
        f"/projects/{project_id}/tasks",
        json={"title": "Breakage", "due_date": far_future, "priority": "urgent"},
        headers=auth_headers,
    ).json()
    assert task["priority_score"] == 10

    closed = client.patch(
        f"/tasks/{task['id']}/status", json={"status": "done"}, headers=auth_headers
    ).json()
    assert closed["priority_score"] is None

    reopened = client.patch(
        f"/tasks/{task['id']}/status", json={"status": "todo"}, headers=auth_headers
    ).json()
    assert reopened["priority_score"] == 10


def test_update_task_can_set_closed_at_manually(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    task = client.post(
        f"/projects/{project_id}/tasks", json={"title": "Backfilled"}, headers=auth_headers
    ).json()
    assert task["closed_at"] is None

    backfilled_date = (date.today() - timedelta(days=5)).isoformat()
    updated = client.patch(
        f"/tasks/{task['id']}",
        json={
            "title": "Backfilled",
            "task_type": "task",
            "priority": "medium",
            "closed_at": backfilled_date,
        },
        headers=auth_headers,
    ).json()
    assert updated["closed_at"].startswith(backfilled_date)

    cleared = client.patch(
        f"/tasks/{task['id']}",
        json={"closed_at": None},
        headers=auth_headers,
    ).json()
    assert cleared["closed_at"] is None


def test_delete_task(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    task = client.post(
        f"/projects/{project_id}/tasks", json={"title": "Disposable"}, headers=auth_headers
    ).json()

    response = client.delete(f"/tasks/{task['id']}", headers=auth_headers)
    assert response.status_code == 204

    assert client.get(f"/tasks/{task['id']}", headers=auth_headers).status_code == 404
    remaining = client.get(f"/projects/{project_id}/tasks", headers=auth_headers).json()
    assert task["id"] not in {i["id"] for i in remaining}


def test_delete_task_with_children_is_rejected(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    parent = client.post(
        f"/projects/{project_id}/tasks", json={"title": "Parent"}, headers=auth_headers
    ).json()
    child = client.post(
        f"/tasks/{parent['id']}/subtasks",
        json={"title": "Child"},
        headers=auth_headers,
    ).json()

    response = client.delete(f"/tasks/{parent['id']}", headers=auth_headers)
    assert response.status_code == 409
    assert response.json()["detail"] == "Task contains subtasks"

    reloaded_child = client.get(f"/tasks/{child['id']}", headers=auth_headers).json()
    assert reloaded_child["parent_task_id"] == parent["id"]


def test_create_subtask_rejects_direct_milestone(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    parent = client.post(
        f"/projects/{project_id}/tasks", json={"title": "Parent"}, headers=auth_headers
    ).json()
    milestone = client.post(
        f"/projects/{project_id}/milestones",
        json={"title": "Release"},
        headers=auth_headers,
    ).json()

    response = client.post(
        f"/tasks/{parent['id']}/subtasks",
        json={"title": "Child", "milestone_id": milestone["id"]},
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Subtasks cannot be assigned directly to a Milestone"


def test_delete_task_404_for_unknown_task(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.delete(f"/tasks/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404
