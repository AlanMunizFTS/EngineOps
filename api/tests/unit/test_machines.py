import uuid

from fakes import FakeAuditLog
from fastapi.testclient import TestClient


def _create_project(client: TestClient, auth_headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Line 4 Retrofit"}, headers=auth_headers)
    return response.json()["id"]


def test_create_machine(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)

    response = client.post(
        f"/projects/{project_id}/machines",
        json={"name": "Cell 4A Robot", "machine_type": "robot cell", "location": "Line 4"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["project_id"] == project_id
    assert body["name"] == "Cell 4A Robot"


def test_create_machine_404_for_unknown_project(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        f"/projects/{uuid.uuid4()}/machines", json={"name": "Cell X"}, headers=auth_headers
    )
    assert response.status_code == 404


def test_list_project_machines_returns_all_attached(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    client.post(f"/projects/{project_id}/machines", json={"name": "Cell 4A"}, headers=auth_headers)
    client.post(f"/projects/{project_id}/machines", json={"name": "Cell 4B"}, headers=auth_headers)

    machines = client.get(f"/projects/{project_id}/machines", headers=auth_headers).json()
    assert len(machines) == 2
    assert {m["name"] for m in machines} == {"Cell 4A", "Cell 4B"}


def test_create_implementation_records_audit_with_project_id(
    client: TestClient, auth_headers: dict[str, str], fake_audit_log: FakeAuditLog
) -> None:
    project_id = _create_project(client, auth_headers)
    machine_id = client.post(
        f"/projects/{project_id}/machines", json={"name": "Cell 4A"}, headers=auth_headers
    ).json()["id"]

    response = client.post(
        f"/machines/{machine_id}/implementations",
        json={"label": "v1 - initial install", "status": "active"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["machine_id"] == machine_id

    created_entry = next(
        entry for entry in fake_audit_log.entries if entry.action == "implementation.created"
    )
    assert str(created_entry.project_id) == project_id


def test_list_machine_implementations_returns_all_attached(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    machine_id = client.post(
        f"/projects/{project_id}/machines", json={"name": "Cell 4A"}, headers=auth_headers
    ).json()["id"]
    client.post(
        f"/machines/{machine_id}/implementations", json={"label": "v1"}, headers=auth_headers
    )
    client.post(
        f"/machines/{machine_id}/implementations", json={"label": "v2"}, headers=auth_headers
    )

    implementations = client.get(
        f"/machines/{machine_id}/implementations", headers=auth_headers
    ).json()
    assert len(implementations) == 2
    assert {i["label"] for i in implementations} == {"v1", "v2"}


def test_supersede_implementation_updates_status_and_link(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    machine_id = client.post(
        f"/projects/{project_id}/machines", json={"name": "Cell 4A"}, headers=auth_headers
    ).json()["id"]
    old_impl = client.post(
        f"/machines/{machine_id}/implementations", json={"label": "v1"}, headers=auth_headers
    ).json()
    new_impl = client.post(
        f"/machines/{machine_id}/implementations", json={"label": "v2"}, headers=auth_headers
    ).json()

    response = client.post(
        f"/implementations/{old_impl['id']}/supersede",
        params={"superseded_by": new_impl["id"]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "superseded"
    assert body["superseded_by"] == new_impl["id"]
