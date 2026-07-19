import uuid

from fakes import FakeAreaRepository, FakeAuditLog
from fastapi.testclient import TestClient


def _create_project(client: TestClient, auth_headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Endforms"}, headers=auth_headers)
    return response.json()["id"]


def test_create_plant(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)

    response = client.post(
        f"/projects/{project_id}/plants",
        json={"name": "Plant A", "location": "Monterrey"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["project_id"] == project_id
    assert body["name"] == "Plant A"
    assert body["location"] == "Monterrey"


def test_create_plant_404_for_unknown_project(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        f"/projects/{uuid.uuid4()}/plants", json={"name": "Plant X"}, headers=auth_headers
    )
    assert response.status_code == 404


def test_list_project_plants_returns_all_attached(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    client.post(f"/projects/{project_id}/plants", json={"name": "Plant A"}, headers=auth_headers)
    client.post(f"/projects/{project_id}/plants", json={"name": "Plant B"}, headers=auth_headers)

    plants = client.get(f"/projects/{project_id}/plants", headers=auth_headers).json()
    assert len(plants) == 2
    assert {p["name"] for p in plants} == {"Plant A", "Plant B"}


def test_create_plant_records_audit_entry(
    client: TestClient, auth_headers: dict[str, str], fake_audit_log: FakeAuditLog
) -> None:
    project_id = _create_project(client, auth_headers)
    client.post(f"/projects/{project_id}/plants", json={"name": "Plant A"}, headers=auth_headers)

    created_entry = next(
        entry for entry in fake_audit_log.entries if entry.action == "plant.created"
    )
    assert str(created_entry.project_id) == project_id


def test_plant_has_no_phase_override_by_default(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    plant = client.post(
        f"/projects/{project_id}/plants", json={"name": "Plant A"}, headers=auth_headers
    ).json()
    assert plant["phase_status"] is None


def test_set_and_clear_plant_phase_override(
    client: TestClient,
    auth_headers: dict[str, str],
    fake_audit_log: FakeAuditLog,
    fake_area_repository: FakeAreaRepository,
) -> None:
    project_id = _create_project(client, auth_headers)
    plant_id = client.post(
        f"/projects/{project_id}/plants", json={"name": "Plant A"}, headers=auth_headers
    ).json()["id"]
    status_id = str(fake_area_repository._statuses[1].id)

    response = client.patch(
        f"/plants/{plant_id}/phase", json={"status_id": status_id}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["phase_status"]["id"] == status_id

    changed_entry = next(
        entry for entry in fake_audit_log.entries if entry.action == "plant.phase_changed"
    )
    assert changed_entry.diff == {"from": None, "to": "Analyzing"}

    cleared = client.patch(
        f"/plants/{plant_id}/phase", json={"status_id": None}, headers=auth_headers
    )
    assert cleared.status_code == 200
    assert cleared.json()["phase_status"] is None


def test_update_plant_phase_404_for_unknown_plant(
    client: TestClient, auth_headers: dict[str, str], fake_area_repository: FakeAreaRepository
) -> None:
    response = client.patch(
        f"/plants/{uuid.uuid4()}/phase",
        json={"status_id": str(fake_area_repository._statuses[0].id)},
        headers=auth_headers,
    )
    assert response.status_code == 404
