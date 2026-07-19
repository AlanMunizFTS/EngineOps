import uuid

from fastapi.testclient import TestClient


def _create_project(client: TestClient, auth_headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Endforms"}, headers=auth_headers)
    return response.json()["id"]


def _create_milestone(client: TestClient, auth_headers: dict[str, str], project_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/milestones",
        json={"title": "v1.0", "description": "First release"},
        headers=auth_headers,
    )
    return response.json()["id"]


def test_create_milestone(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)

    response = client.post(
        f"/projects/{project_id}/milestones", json={"title": "v1.0"}, headers=auth_headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["project_id"] == project_id
    assert body["title"] == "v1.0"
    assert body["status"] == "open"


def test_create_milestone_404_for_unknown_project(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        f"/projects/{uuid.uuid4()}/milestones", json={"title": "v1.0"}, headers=auth_headers
    )
    assert response.status_code == 404


def test_milestone_progress_reflects_closed_issues(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    milestone_id = _create_milestone(client, auth_headers, project_id)

    issue_a = client.post(
        f"/projects/{project_id}/issues",
        json={"title": "Fix conveyor jam", "milestone_id": milestone_id},
        headers=auth_headers,
    ).json()
    client.post(
        f"/projects/{project_id}/issues",
        json={"title": "Calibrate camera", "milestone_id": milestone_id},
        headers=auth_headers,
    )

    milestones = client.get(f"/projects/{project_id}/milestones", headers=auth_headers).json()
    progress = next(m for m in milestones if m["id"] == milestone_id)
    assert progress["total_issues"] == 2
    assert progress["closed_issues"] == 0
    assert progress["percent_complete"] == 0.0

    client.patch(f"/issues/{issue_a['id']}/status", json={"status": "done"}, headers=auth_headers)

    milestones = client.get(f"/projects/{project_id}/milestones", headers=auth_headers).json()
    progress = next(m for m in milestones if m["id"] == milestone_id)
    assert progress["closed_issues"] == 1
    assert progress["percent_complete"] == 50.0


def test_update_milestone_status_records_audit_entry(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    milestone_id = _create_milestone(client, auth_headers, project_id)

    response = client.patch(
        f"/milestones/{milestone_id}/status", json={"status": "closed"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "closed"

    timeline = client.get(f"/projects/{project_id}/timeline", headers=auth_headers).json()
    assert any(entry["action"] == "milestone.status_changed" for entry in timeline)
