import uuid

from fastapi.testclient import TestClient


def _create_project(client: TestClient, auth_headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Endforms"}, headers=auth_headers)
    return response.json()["id"]


def test_project_creation_seeds_a_default_board_with_5_fixed_columns(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)

    response = client.get(f"/projects/{project_id}/kanban", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == project_id
    assert [column["maps_to_status"] for column in body["columns"]] == [
        "backlog",
        "todo",
        "in_progress",
        "in_review",
        "done",
    ]
    assert [column["order_index"] for column in body["columns"]] == [0, 1, 2, 3, 4]


def test_get_kanban_board_404_for_unknown_project(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get(f"/projects/{uuid.uuid4()}/kanban", headers=auth_headers)
    assert response.status_code == 404


def test_moving_a_card_updates_issue_status_and_records_audit_entry(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    board = client.get(f"/projects/{project_id}/kanban", headers=auth_headers).json()
    in_progress_column = next(c for c in board["columns"] if c["name"] == "In Progress")

    issue = client.post(
        f"/projects/{project_id}/issues", json={"title": "Fix conveyor jam"}, headers=auth_headers
    ).json()
    assert issue["status"] == "backlog"

    response = client.patch(
        f"/issues/{issue['id']}/status",
        json={"status": in_progress_column["maps_to_status"]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"

    timeline = client.get(f"/projects/{project_id}/timeline", headers=auth_headers).json()
    status_change = next(e for e in timeline if e["action"] == "issue.status_changed")
    assert status_change["diff"] == {"from": "backlog", "to": "in_progress"}
