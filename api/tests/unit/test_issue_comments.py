import uuid

from fastapi.testclient import TestClient


def _create_project(client: TestClient, auth_headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Endforms"}, headers=auth_headers)
    return response.json()["id"]


def test_create_and_list_comments(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    issue = client.post(
        f"/projects/{project_id}/issues", json={"title": "Fix conveyor jam"}, headers=auth_headers
    ).json()

    response = client.post(
        f"/issues/{issue['id']}/comments",
        json={"body": "Confirmed the sensor is misaligned, see @jdoe for parts."},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["issue_id"] == issue["id"]
    assert body["edited_at"] is None

    comments = client.get(f"/issues/{issue['id']}/comments", headers=auth_headers).json()
    assert len(comments) == 1
    assert comments[0]["body"] == "Confirmed the sensor is misaligned, see @jdoe for parts."


def test_create_comment_404_for_unknown_issue(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        f"/issues/{uuid.uuid4()}/comments", json={"body": "hi"}, headers=auth_headers
    )
    assert response.status_code == 404


def test_edit_comment_sets_edited_at(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    issue = client.post(
        f"/projects/{project_id}/issues", json={"title": "Fix conveyor jam"}, headers=auth_headers
    ).json()
    comment = client.post(
        f"/issues/{issue['id']}/comments", json={"body": "Initial note"}, headers=auth_headers
    ).json()

    response = client.patch(
        f"/issue-comments/{comment['id']}", json={"body": "Updated note"}, headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["body"] == "Updated note"
    assert body["edited_at"] is not None


def test_full_dod_flow_create_move_comment_appear_in_timeline(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Mirrors Phase 2's DoD: create an issue, move it across kanban columns,
    add a comment, confirm all three actions appear correctly ordered in the
    project timeline."""
    project_id = _create_project(client, auth_headers)

    issue = client.post(
        f"/projects/{project_id}/issues", json={"title": "Fix conveyor jam"}, headers=auth_headers
    ).json()
    client.patch(
        f"/issues/{issue['id']}/status", json={"status": "in_progress"}, headers=auth_headers
    )
    client.patch(f"/issues/{issue['id']}/status", json={"status": "done"}, headers=auth_headers)
    client.post(
        f"/issues/{issue['id']}/comments", json={"body": "Done, verified."}, headers=auth_headers
    )

    timeline = client.get(f"/projects/{project_id}/timeline", headers=auth_headers).json()
    actions_in_order = [entry["action"] for entry in timeline]
    assert actions_in_order == [
        "project.created",
        "issue.created",
        "issue.status_changed",
        "issue.status_changed",
        "issue.comment_added",
    ]
