from fastapi.testclient import TestClient


def _create_project(client: TestClient, headers: dict[str, str], name: str = "Engine") -> str:
    return client.post("/projects", json={"name": name}, headers=headers).json()["id"]


def test_milestone_crud_and_progress_counts_only_top_level_tasks(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    milestone = client.post(
        f"/projects/{project_id}/milestones",
        json={"title": "Validation", "description": "Ship-ready checks"},
        headers=auth_headers,
    ).json()

    first = client.post(
        f"/projects/{project_id}/tasks",
        json={"title": "First", "milestone_id": milestone["id"]},
        headers=auth_headers,
    ).json()
    client.post(
        f"/projects/{project_id}/tasks",
        json={"title": "Second", "milestone_id": milestone["id"]},
        headers=auth_headers,
    )
    subtask = client.post(
        f"/tasks/{first['id']}/subtasks",
        json={"title": "Direct child"},
        headers=auth_headers,
    ).json()
    client.patch(f"/tasks/{subtask['id']}/status", json={"status": "done"}, headers=auth_headers)
    client.patch(f"/tasks/{first['id']}/status", json={"status": "done"}, headers=auth_headers)

    response = client.get(f"/milestones/{milestone['id']}", headers=auth_headers)
    assert response.status_code == 200
    progress = response.json()
    assert progress["total_tasks"] == 2
    assert progress["completed_tasks"] == 1
    assert progress["progress_percentage"] == 50.0

    updated = client.patch(
        f"/milestones/{milestone['id']}",
        json={"title": "Validation complete", "status": "closed"},
        headers=auth_headers,
    ).json()
    assert updated["title"] == "Validation complete"
    assert updated["status"] == "closed"


def test_deleting_milestone_keeps_tasks_and_clears_assignment(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers, "Deletion")
    milestone = client.post(
        f"/projects/{project_id}/milestones",
        json={"title": "Temporary"},
        headers=auth_headers,
    ).json()
    task = client.post(
        f"/projects/{project_id}/tasks",
        json={"title": "Survivor", "milestone_id": milestone["id"]},
        headers=auth_headers,
    ).json()

    response = client.delete(f"/milestones/{milestone['id']}", headers=auth_headers)
    assert response.status_code == 204
    assert client.get(f"/milestones/{milestone['id']}", headers=auth_headers).status_code == 404
    surviving_task = client.get(f"/tasks/{task['id']}", headers=auth_headers).json()
    assert surviving_task["milestone_id"] is None
