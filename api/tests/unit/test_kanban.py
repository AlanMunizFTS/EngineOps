import uuid

from fastapi.testclient import TestClient


def _create_project(client: TestClient, auth_headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Endforms"}, headers=auth_headers)
    return response.json()["id"]


def _default_board(client: TestClient, project_id: str, auth_headers: dict[str, str]) -> dict:
    boards = client.get(f"/projects/{project_id}/kanban-boards", headers=auth_headers).json()
    return boards[0]


def test_project_creation_seeds_a_default_board_with_5_fixed_columns(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)

    board = _default_board(client, project_id, auth_headers)
    assert board["project_id"] == project_id
    assert [column["maps_to_statuses"] for column in board["columns"]] == [
        ["backlog"],
        ["todo"],
        ["in_progress"],
        ["in_review"],
        ["done"],
    ]
    assert [column["order_index"] for column in board["columns"]] == [0, 1, 2, 3, 4]


def test_list_kanban_boards_404_for_unknown_project(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get(f"/projects/{uuid.uuid4()}/kanban-boards", headers=auth_headers)
    assert response.status_code == 404


def test_moving_a_card_updates_task_status_and_records_audit_entry(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    board = _default_board(client, project_id, auth_headers)
    in_progress_column = next(c for c in board["columns"] if c["name"] == "In Progress")

    task = client.post(
        f"/projects/{project_id}/tasks", json={"title": "Fix conveyor jam"}, headers=auth_headers
    ).json()
    assert task["status"] == "backlog"

    response = client.patch(
        f"/tasks/{task['id']}/status",
        json={"status": in_progress_column["maps_to_statuses"][0]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"

    timeline = client.get(f"/projects/{project_id}/timeline", headers=auth_headers).json()
    status_change = next(e for e in timeline if e["action"] == "task.status_changed")
    assert status_change["diff"] == {
        "old_status": "backlog",
        "new_status": "in_progress",
    }


def test_create_a_second_board(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)

    response = client.post(
        f"/projects/{project_id}/kanban-boards",
        json={"name": "Release view"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    board = response.json()
    assert board["name"] == "Release view"
    # New boards seed the same 5 default columns as the auto-created one, so
    # every existing task lands somewhere immediately.
    assert [c["maps_to_statuses"] for c in board["columns"]] == [
        ["backlog"],
        ["todo"],
        ["in_progress"],
        ["in_review"],
        ["done"],
    ]

    boards = client.get(f"/projects/{project_id}/kanban-boards", headers=auth_headers).json()
    assert {b["name"] for b in boards} == {"Board", "Release view"}


def test_create_board_404_for_unknown_project(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        f"/projects/{uuid.uuid4()}/kanban-boards", json={"name": "X"}, headers=auth_headers
    )
    assert response.status_code == 404


def test_rename_board(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    board = _default_board(client, project_id, auth_headers)

    response = client.patch(
        f"/kanban-boards/{board['id']}", json={"name": "Renamed"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


def test_delete_board(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    created = client.post(
        f"/projects/{project_id}/kanban-boards", json={"name": "Temp"}, headers=auth_headers
    ).json()

    response = client.delete(f"/kanban-boards/{created['id']}", headers=auth_headers)
    assert response.status_code == 204

    boards = client.get(f"/projects/{project_id}/kanban-boards", headers=auth_headers).json()
    assert {b["id"] for b in boards} == {_default_board(client, project_id, auth_headers)["id"]}


def test_create_column_with_multiple_statuses(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    board = client.post(
        f"/projects/{project_id}/kanban-boards", json={"name": "Custom"}, headers=auth_headers
    ).json()

    response = client.post(
        f"/kanban-boards/{board['id']}/columns",
        json={"name": "Active", "maps_to_statuses": ["todo", "in_progress"]},
        headers=auth_headers,
    )
    assert response.status_code == 201
    column = response.json()
    assert column["name"] == "Active"
    assert column["maps_to_statuses"] == ["todo", "in_progress"]
    # Appended after the 5 seeded default columns (indices 0-4).
    assert column["order_index"] == 5


def test_update_column_name_and_mapping(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    board = _default_board(client, project_id, auth_headers)
    column = board["columns"][0]

    response = client.patch(
        f"/kanban-columns/{column['id']}",
        json={"name": "Renamed column", "maps_to_statuses": ["done"]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Renamed column"
    assert body["maps_to_statuses"] == ["done"]


def test_delete_column(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    board = _default_board(client, project_id, auth_headers)
    column = board["columns"][0]

    response = client.delete(f"/kanban-columns/{column['id']}", headers=auth_headers)
    assert response.status_code == 204

    updated_board = client.get(f"/kanban-boards/{board['id']}", headers=auth_headers).json()
    assert column["id"] not in [c["id"] for c in updated_board["columns"]]


def test_delete_column_404_for_unknown_column(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.delete(f"/kanban-columns/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_reorder_columns(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    board = _default_board(client, project_id, auth_headers)
    column_ids = [c["id"] for c in board["columns"]]
    reversed_ids = list(reversed(column_ids))

    response = client.patch(
        f"/kanban-boards/{board['id']}/columns/reorder",
        json={"ordered_column_ids": reversed_ids},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert [c["id"] for c in body["columns"]] == reversed_ids
    assert [c["order_index"] for c in body["columns"]] == [0, 1, 2, 3, 4]


def test_reorder_columns_400_when_ids_do_not_match_board(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    board = _default_board(client, project_id, auth_headers)

    response = client.patch(
        f"/kanban-boards/{board['id']}/columns/reorder",
        json={"ordered_column_ids": [str(uuid.uuid4())]},
        headers=auth_headers,
    )
    assert response.status_code == 400
