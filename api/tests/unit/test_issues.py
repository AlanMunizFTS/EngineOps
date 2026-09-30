import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient

from ops_platform.api.routers.issues import _issue_response
from ops_platform.domain.entities import Issue, IssuePriority, IssueStatus, IssueType


def _create_project(client: TestClient, auth_headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Endforms"}, headers=auth_headers)
    return response.json()["id"]


def test_issue_response_closed_at_date_uses_business_timezone_not_utc() -> None:
    # 19:00 on the 23rd at UTC-6 is already 01:00 on the 24th in UTC - the
    # closed_at_date shown to the user must track the former, not the raw
    # UTC calendar day closed_at happens to serialize under.
    issue = Issue(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        title="Late shift close",
        description=None,
        status=IssueStatus.DONE,
        priority=IssuePriority.MEDIUM,
        issue_type=IssueType.TASK,
        assignee_id=None,
        created_by=None,
        created_at=datetime(2026, 7, 23, 12, 0, tzinfo=UTC),
        closed_at=datetime(2026, 7, 24, 1, 0, tzinfo=UTC),
    )

    response = _issue_response(issue)

    assert response.closed_at is not None
    assert response.closed_at.date() == date(2026, 7, 24)
    assert response.closed_at_date == date(2026, 7, 23)


def test_create_issue_defaults_to_backlog(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)

    response = client.post(
        f"/projects/{project_id}/issues", json={"title": "Fix conveyor jam"}, headers=auth_headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["project_id"] == project_id
    assert body["status"] == "backlog"
    assert body["priority"] == "medium"
    assert body["issue_type"] == "task"
    assert body["labels"] == []


def test_create_issue_records_audit_entry(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    client.post(
        f"/projects/{project_id}/issues", json={"title": "Fix conveyor jam"}, headers=auth_headers
    )

    timeline = client.get(f"/projects/{project_id}/timeline", headers=auth_headers).json()
    assert any(entry["action"] == "issue.created" for entry in timeline)


def test_list_project_issues_filters_by_status(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    open_issue = client.post(
        f"/projects/{project_id}/issues", json={"title": "Open issue"}, headers=auth_headers
    ).json()
    done_issue = client.post(
        f"/projects/{project_id}/issues", json={"title": "Done issue"}, headers=auth_headers
    ).json()
    client.patch(
        f"/issues/{done_issue['id']}/status", json={"status": "done"}, headers=auth_headers
    )

    backlog_issues = client.get(
        f"/projects/{project_id}/issues", params={"status": "backlog"}, headers=auth_headers
    ).json()
    assert {i["id"] for i in backlog_issues} == {open_issue["id"]}

    done_issues = client.get(
        f"/projects/{project_id}/issues", params={"status": "done"}, headers=auth_headers
    ).json()
    assert {i["id"] for i in done_issues} == {done_issue["id"]}


def test_list_project_issues_auto_advances_backlog_to_todo_on_start_date(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    today = date.today().isoformat()
    due = client.post(
        f"/projects/{project_id}/issues",
        json={"title": "Starts today", "start_date": today},
        headers=auth_headers,
    ).json()
    assert due["status"] == "backlog"

    issues = client.get(f"/projects/{project_id}/issues", headers=auth_headers).json()
    advanced = next(i for i in issues if i["id"] == due["id"])
    assert advanced["status"] == "todo"


def test_list_project_issues_leaves_future_start_dates_in_backlog(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    far_future = (date.today() + timedelta(days=30)).isoformat()
    issue = client.post(
        f"/projects/{project_id}/issues",
        json={"title": "Not yet", "start_date": far_future},
        headers=auth_headers,
    ).json()

    issues = client.get(f"/projects/{project_id}/issues", headers=auth_headers).json()
    unchanged = next(i for i in issues if i["id"] == issue["id"])
    assert unchanged["status"] == "backlog"


def test_list_project_issues_does_not_auto_advance_issues_moved_out_of_backlog(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    today = date.today().isoformat()
    issue = client.post(
        f"/projects/{project_id}/issues",
        json={"title": "Manually moved", "start_date": today},
        headers=auth_headers,
    ).json()
    client.patch(
        f"/issues/{issue['id']}/status", json={"status": "in_progress"}, headers=auth_headers
    )

    issues = client.get(f"/projects/{project_id}/issues", headers=auth_headers).json()
    unchanged = next(i for i in issues if i["id"] == issue["id"])
    assert unchanged["status"] == "in_progress"


def test_update_issue_status_sets_and_clears_closed_at(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    issue = client.post(
        f"/projects/{project_id}/issues", json={"title": "Fix conveyor jam"}, headers=auth_headers
    ).json()
    assert issue["closed_at"] is None

    closed = client.patch(
        f"/issues/{issue['id']}/status", json={"status": "done"}, headers=auth_headers
    ).json()
    assert closed["closed_at"] is not None

    reopened = client.patch(
        f"/issues/{issue['id']}/status", json={"status": "todo"}, headers=auth_headers
    ).json()
    assert reopened["closed_at"] is None


def test_attach_and_detach_label(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    issue = client.post(
        f"/projects/{project_id}/issues", json={"title": "Fix conveyor jam"}, headers=auth_headers
    ).json()
    label = client.post(
        f"/projects/{project_id}/labels",
        json={"name": "bug", "color": "#ff0000"},
        headers=auth_headers,
    ).json()

    attached = client.post(
        f"/issues/{issue['id']}/labels", json={"label_id": label["id"]}, headers=auth_headers
    ).json()
    assert [label_out["id"] for label_out in attached["labels"]] == [label["id"]]

    filtered = client.get(
        f"/projects/{project_id}/issues", params={"label_id": label["id"]}, headers=auth_headers
    ).json()
    assert {i["id"] for i in filtered} == {issue["id"]}

    detached = client.delete(
        f"/issues/{issue['id']}/labels/{label['id']}", headers=auth_headers
    ).json()
    assert detached["labels"] == []


def test_update_issue(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    issue = client.post(
        f"/projects/{project_id}/issues", json={"title": "Fix conveyor jam"}, headers=auth_headers
    ).json()

    response = client.patch(
        f"/issues/{issue['id']}",
        json={
            "title": "Fix conveyor jam - urgent",
            "description": "Line 4 is down",
            "issue_type": "bug",
            "priority": "urgent",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Fix conveyor jam - urgent"
    assert body["priority"] == "urgent"
    assert body["issue_type"] == "bug"


def test_get_issue_404_for_unknown_id(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get(f"/issues/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_create_issue_without_schedule_fields_has_null_computed_fields(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)

    issue = client.post(
        f"/projects/{project_id}/issues", json={"title": "No schedule"}, headers=auth_headers
    ).json()
    assert issue["parent_issue_id"] is None
    assert issue["start_date"] is None
    assert issue["due_date"] is None
    assert issue["days_planned"] is None
    assert issue["days_taken"] is None
    assert issue["urgency"] is None
    assert issue["priority_score"] is None
    assert issue["schedule_status"] is None


def test_create_issue_with_schedule_fields(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    today = date.today()

    issue = client.post(
        f"/projects/{project_id}/issues",
        json={
            "title": "Wrinkle",
            "start_date": today.isoformat(),
            "due_date": today.isoformat(),
        },
        headers=auth_headers,
    ).json()
    assert issue["start_date"] == today.isoformat()
    assert issue["due_date"] == today.isoformat()
    # Same-day span, both endpoints inclusive -> 1 working day planned
    # (unless today happens to be a weekend, in which case 0).
    assert issue["days_planned"] in (0, 1)
    # Due today -> 0 working days remaining -> High urgency.
    assert issue["urgency"] == "high"
    assert issue["schedule_status"] == "on_time"
    # Importance defaults to medium; High urgency x Medium importance = 8.
    assert issue["priority_score"] == 8


def test_issue_urgency_low_for_far_future_due_date(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    far_future = (date.today() + timedelta(days=30)).isoformat()

    issue = client.post(
        f"/projects/{project_id}/issues",
        json={"title": "Split", "due_date": far_future, "priority": "low"},
        headers=auth_headers,
    ).json()
    assert issue["urgency"] == "low"
    # Low urgency x Low importance = 1.
    assert issue["priority_score"] == 1


def test_issue_priority_score_is_ten_when_importance_is_urgent_regardless_of_urgency(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    far_future = (date.today() + timedelta(days=30)).isoformat()

    issue = client.post(
        f"/projects/{project_id}/issues",
        json={"title": "Breakage", "due_date": far_future, "priority": "urgent"},
        headers=auth_headers,
    ).json()
    assert issue["urgency"] == "low"
    assert issue["priority_score"] == 10


def test_issue_schedule_status_late_when_overdue_and_open(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    overdue = (date.today() - timedelta(days=10)).isoformat()

    issue = client.post(
        f"/projects/{project_id}/issues",
        json={"title": "Edge", "due_date": overdue},
        headers=auth_headers,
    ).json()
    assert issue["schedule_status"] == "late"
    assert issue["urgency"] == "high"
    # Overdue always scores 10, regardless of importance (default: medium).
    assert issue["priority_score"] == 10


def test_issue_priority_score_zero_when_start_date_in_future(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    due_today = date.today().isoformat()

    issue = client.post(
        f"/projects/{project_id}/issues",
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
    assert issue["priority_score"] == 0


def test_issue_priority_score_normal_when_due_today_not_overdue(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    today = date.today().isoformat()

    issue = client.post(
        f"/projects/{project_id}/issues",
        json={"title": "Due today", "due_date": today, "priority": "low"},
        headers=auth_headers,
    ).json()
    assert issue["schedule_status"] == "on_time"
    assert issue["urgency"] == "high"
    # Due today (not overdue) still uses the normal matrix: HIGH urgency x
    # LOW importance = 2*3 + 1 = 7, not the overdue override of 10.
    assert issue["priority_score"] == 7


def test_issue_schedule_status_closed_after_done(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    today = date.today()
    issue = client.post(
        f"/projects/{project_id}/issues",
        json={"title": "Nylon", "start_date": today.isoformat(), "due_date": today.isoformat()},
        headers=auth_headers,
    ).json()

    closed = client.patch(
        f"/issues/{issue['id']}/status", json={"status": "done"}, headers=auth_headers
    ).json()
    assert closed["schedule_status"] == "closed"
    assert closed["days_taken"] == 0


def test_update_issue_preserves_schedule_fields(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    today = date.today().isoformat()
    issue = client.post(
        f"/projects/{project_id}/issues",
        json={"title": "Streaked", "start_date": today, "due_date": today},
        headers=auth_headers,
    ).json()

    updated = client.patch(
        f"/issues/{issue['id']}",
        json={
            "title": "Streaked",
            "issue_type": "task",
            "priority": "medium",
            "start_date": today,
            "due_date": today,
        },
        headers=auth_headers,
    ).json()
    assert updated["start_date"] == today
    assert updated["due_date"] == today


def test_issue_can_have_a_parent(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    parent = client.post(
        f"/projects/{project_id}/issues",
        json={"title": "Mushroom Validation"},
        headers=auth_headers,
    ).json()

    child = client.post(
        f"/projects/{project_id}/issues",
        json={"title": "Wrinkle", "parent_issue_id": parent["id"]},
        headers=auth_headers,
    ).json()
    assert child["parent_issue_id"] == parent["id"]

    reparented = client.patch(
        f"/issues/{child['id']}",
        json={
            "title": "Wrinkle",
            "issue_type": "task",
            "priority": "medium",
            "parent_issue_id": None,
        },
        headers=auth_headers,
    ).json()
    assert reparented["parent_issue_id"] is None


def _set_parent(
    client: TestClient, auth_headers: dict[str, str], issue: dict, parent_id: str | None
) -> dict:
    return client.patch(
        f"/issues/{issue['id']}",
        json={
            "title": issue["title"],
            "issue_type": issue["issue_type"],
            "priority": issue["priority"],
            "parent_issue_id": parent_id,
        },
        headers=auth_headers,
    ).json()


def test_relinking_a_parent_bumps_parent_assigned_at(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Reproduces the reported bug: unlink issue A from a parent, link B in
    the meantime, then re-link A - A's parent_assigned_at should now be
    *after* B's, so the Schedule view (which sorts siblings by
    parent_assigned_at, not created_at) numbers B before A even though A
    was created first."""
    project_id = _create_project(client, auth_headers)
    parent = client.post(
        f"/projects/{project_id}/issues", json={"title": "Parent"}, headers=auth_headers
    ).json()
    issue_a = client.post(
        f"/projects/{project_id}/issues",
        json={"title": "A", "parent_issue_id": parent["id"]},
        headers=auth_headers,
    ).json()
    assert issue_a["parent_assigned_at"] is not None

    unlinked = _set_parent(client, auth_headers, issue_a, None)
    assert unlinked["parent_assigned_at"] is None

    issue_b = client.post(
        f"/projects/{project_id}/issues",
        json={"title": "B", "parent_issue_id": parent["id"]},
        headers=auth_headers,
    ).json()

    relinked_a = _set_parent(client, auth_headers, issue_a, parent["id"])
    assert relinked_a["parent_assigned_at"] is not None
    assert relinked_a["parent_assigned_at"] > issue_b["parent_assigned_at"]


def test_issue_history_tracks_status_transitions(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    issue = client.post(
        f"/projects/{project_id}/issues", json={"title": "Fix conveyor jam"}, headers=auth_headers
    ).json()

    client.patch(f"/issues/{issue['id']}/status", json={"status": "todo"}, headers=auth_headers)
    client.patch(
        f"/issues/{issue['id']}/status", json={"status": "in_progress"}, headers=auth_headers
    )
    client.patch(f"/issues/{issue['id']}/status", json={"status": "done"}, headers=auth_headers)

    history = client.get(f"/issues/{issue['id']}/history", headers=auth_headers).json()
    status_changes = [e for e in history if e["action"] == "issue.status_changed"]
    assert [e["diff"]["to"] for e in status_changes] == ["todo", "in_progress", "done"]
    assert all(e["entity_id"] == issue["id"] for e in history)


def test_my_pending_issues_span_projects_and_only_include_current_user(
    client: TestClient,
    auth_headers: dict[str, str],
    current_user,
) -> None:
    first_project_id = _create_project(client, auth_headers)
    second_project_id = _create_project(client, auth_headers)

    first = client.post(
        f"/projects/{first_project_id}/issues",
        json={"title": "First assigned task", "assignee_id": str(current_user.id)},
        headers=auth_headers,
    ).json()
    second = client.post(
        f"/projects/{second_project_id}/issues",
        json={"title": "Second assigned task", "assignee_id": str(current_user.id)},
        headers=auth_headers,
    ).json()
    client.post(
        f"/projects/{first_project_id}/issues",
        json={"title": "Unassigned task"},
        headers=auth_headers,
    )
    completed = client.post(
        f"/projects/{second_project_id}/issues",
        json={"title": "Completed task", "assignee_id": str(current_user.id)},
        headers=auth_headers,
    ).json()
    client.patch(
        f"/issues/{completed['id']}/status",
        json={"status": "done"},
        headers=auth_headers,
    )

    response = client.get("/issues/assigned-to-me", headers=auth_headers)

    assert response.status_code == 200
    assert {issue["id"] for issue in response.json()} == {first["id"], second["id"]}


def test_my_pending_issues_requires_authentication(client: TestClient) -> None:
    assert client.get("/issues/assigned-to-me").status_code == 401


def test_issue_history_404_for_unknown_issue(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get(f"/issues/{uuid.uuid4()}/history", headers=auth_headers)
    assert response.status_code == 404


def test_priority_score_is_none_once_issue_is_done(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    far_future = (date.today() + timedelta(days=30)).isoformat()
    issue = client.post(
        f"/projects/{project_id}/issues",
        json={"title": "Breakage", "due_date": far_future, "priority": "urgent"},
        headers=auth_headers,
    ).json()
    assert issue["priority_score"] == 10

    closed = client.patch(
        f"/issues/{issue['id']}/status", json={"status": "done"}, headers=auth_headers
    ).json()
    assert closed["priority_score"] is None

    reopened = client.patch(
        f"/issues/{issue['id']}/status", json={"status": "todo"}, headers=auth_headers
    ).json()
    assert reopened["priority_score"] == 10


def test_update_issue_can_set_closed_at_manually(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    issue = client.post(
        f"/projects/{project_id}/issues", json={"title": "Backfilled"}, headers=auth_headers
    ).json()
    assert issue["closed_at"] is None

    backfilled_date = (date.today() - timedelta(days=5)).isoformat()
    updated = client.patch(
        f"/issues/{issue['id']}",
        json={
            "title": "Backfilled",
            "issue_type": "task",
            "priority": "medium",
            "closed_at": backfilled_date,
        },
        headers=auth_headers,
    ).json()
    assert updated["closed_at"].startswith(backfilled_date)

    cleared = client.patch(
        f"/issues/{issue['id']}",
        json={"title": "Backfilled", "issue_type": "task", "priority": "medium"},
        headers=auth_headers,
    ).json()
    assert cleared["closed_at"] is None


def test_delete_issue(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    issue = client.post(
        f"/projects/{project_id}/issues", json={"title": "Disposable"}, headers=auth_headers
    ).json()

    response = client.delete(f"/issues/{issue['id']}", headers=auth_headers)
    assert response.status_code == 204

    assert client.get(f"/issues/{issue['id']}", headers=auth_headers).status_code == 404
    remaining = client.get(f"/projects/{project_id}/issues", headers=auth_headers).json()
    assert issue["id"] not in {i["id"] for i in remaining}


def test_delete_issue_orphans_children(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    parent = client.post(
        f"/projects/{project_id}/issues", json={"title": "Parent"}, headers=auth_headers
    ).json()
    child = client.post(
        f"/projects/{project_id}/issues",
        json={"title": "Child", "parent_issue_id": parent["id"]},
        headers=auth_headers,
    ).json()

    client.delete(f"/issues/{parent['id']}", headers=auth_headers)

    reloaded_child = client.get(f"/issues/{child['id']}", headers=auth_headers).json()
    assert reloaded_child["parent_issue_id"] is None


def test_delete_issue_404_for_unknown_issue(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.delete(f"/issues/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404
