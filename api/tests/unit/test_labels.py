import uuid

from fastapi.testclient import TestClient


def _create_project(client: TestClient, auth_headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Endforms"}, headers=auth_headers)
    return response.json()["id"]


def test_create_label(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)

    response = client.post(
        f"/projects/{project_id}/labels",
        json={"name": "bug", "color": "#ff0000"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["project_id"] == project_id
    assert body["name"] == "bug"
    assert body["color"] == "#ff0000"


def test_create_label_404_for_unknown_project(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        f"/projects/{uuid.uuid4()}/labels",
        json={"name": "bug", "color": "#ff0000"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_list_project_labels_returns_all_created(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    client.post(
        f"/projects/{project_id}/labels",
        json={"name": "bug", "color": "#ff0000"},
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/labels",
        json={"name": "enhancement", "color": "#00ff00"},
        headers=auth_headers,
    )

    labels = client.get(f"/projects/{project_id}/labels", headers=auth_headers).json()
    assert {label["name"] for label in labels} == {"bug", "enhancement"}
