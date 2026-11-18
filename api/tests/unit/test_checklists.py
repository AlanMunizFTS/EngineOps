from fastapi.testclient import TestClient


def test_project_checklist_can_be_attached_and_completed_per_task(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project = client.post("/projects", json={"name": "Vision"}, headers=auth_headers).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "Startup machine", "repeat_daily": True},
        headers=auth_headers,
    ).json()
    checklist_response = client.post(
        f"/projects/{project['id']}/checklists",
        json={"name": "Safe startup"},
        headers=auth_headers,
    )
    assert checklist_response.status_code == 201
    checklist = checklist_response.json()
    item = client.post(
        f"/checklists/{checklist['id']}/items",
        json={"content": "Inspect guards"},
        headers=auth_headers,
    ).json()

    attached = client.post(
        f"/tasks/{task['id']}/checklists/{checklist['id']}", headers=auth_headers
    )
    assert attached.status_code == 200
    assert attached.json()["items"][0]["completed"] is False

    completed = client.patch(
        f"/tasks/{task['id']}/checklist-items/{item['id']}",
        json={"completed": True},
        headers=auth_headers,
    )
    assert completed.status_code == 200
    assert completed.json()["items"][0]["completed"] is True

    done = client.patch(
        f"/tasks/{task['id']}/status", json={"status": "done"}, headers=auth_headers
    )
    assert done.status_code == 200
    project_tasks = client.get(f"/projects/{project['id']}/tasks", headers=auth_headers).json()
    next_task = next(value for value in project_tasks if value["id"] != task["id"])
    next_checklists = client.get(
        f"/tasks/{next_task['id']}/checklists", headers=auth_headers
    ).json()
    assert next_checklists[0]["id"] == checklist["id"]
    assert next_checklists[0]["items"][0]["completed"] is False
