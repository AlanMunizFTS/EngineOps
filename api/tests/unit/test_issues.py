import uuid

from fastapi.testclient import TestClient


def _create_project(client: TestClient, auth_headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Endforms"}, headers=auth_headers)
    return response.json()["id"]


def _create_plant(client: TestClient, auth_headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/plants", json={"name": "Plant A"}, headers=auth_headers
    )
    return response.json()["id"]


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
    assert body["plant_id"] is None
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


def test_create_issue_rejects_more_than_one_hierarchy_link(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    plant_id = _create_plant(client, auth_headers, project_id)

    response = client.post(
        f"/projects/{project_id}/issues",
        json={"title": "Ambiguous link", "plant_id": plant_id, "machine_id": str(uuid.uuid4())},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_issue_404_when_plant_belongs_to_another_project(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_a = _create_project(client, auth_headers)
    project_b = _create_project(client, auth_headers)
    plant_in_b = _create_plant(client, auth_headers, project_b)

    response = client.post(
        f"/projects/{project_a}/issues",
        json={"title": "Cross-project link", "plant_id": plant_in_b},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_create_issue_links_to_a_plant(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    plant_id = _create_plant(client, auth_headers, project_id)

    response = client.post(
        f"/projects/{project_id}/issues",
        json={"title": "Plant-wide rollout issue", "plant_id": plant_id},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["plant_id"] == plant_id


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
