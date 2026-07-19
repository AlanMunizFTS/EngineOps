import uuid

from fakes import FakeAuditLog
from fastapi.testclient import TestClient

from ops_platform.domain.entities import User


def test_create_project_creates_owner_membership_and_default_areas(
    client: TestClient, auth_headers: dict[str, str], current_user: User
) -> None:
    response = client.post(
        "/projects", json={"name": "Line 4 Vision Retrofit"}, headers=auth_headers
    )
    assert response.status_code == 201
    project_id = response.json()["id"]

    members = client.get(f"/projects/{project_id}/members", headers=auth_headers).json()
    assert len(members) == 1
    assert members[0]["user_id"] == str(current_user.id)
    assert members[0]["project_role"] == "owner"

    areas = client.get(f"/projects/{project_id}/areas", headers=auth_headers).json()
    assert len(areas) == 1
    assert areas[0]["status"]["name"] == "Requested"


def test_create_project_records_audit_entry(
    client: TestClient, auth_headers: dict[str, str], fake_audit_log: FakeAuditLog
) -> None:
    response = client.post("/projects", json={"name": "Line 5 Retrofit"}, headers=auth_headers)
    project_id = response.json()["id"]

    actions = [entry.action for entry in fake_audit_log.entries]
    assert "project.created" in actions
    assert all(str(entry.project_id) == project_id for entry in fake_audit_log.entries)


def test_get_project_404_for_unknown_id(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get(f"/projects/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_add_project_member(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = client.post(
        "/projects", json={"name": "Line 6 Retrofit"}, headers=auth_headers
    ).json()["id"]

    new_member_id = str(uuid.uuid4())
    response = client.post(
        f"/projects/{project_id}/members",
        json={"user_id": new_member_id, "project_role": "contributor"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["project_role"] == "contributor"

    members = client.get(f"/projects/{project_id}/members", headers=auth_headers).json()
    assert len(members) == 2


def test_update_project_area_status_records_audit_diff(
    client: TestClient, auth_headers: dict[str, str], fake_audit_log: FakeAuditLog
) -> None:
    project_id = client.post(
        "/projects", json={"name": "Line 7 Retrofit"}, headers=auth_headers
    ).json()["id"]
    areas = client.get(f"/projects/{project_id}/areas", headers=auth_headers).json()
    area = areas[0]

    statuses = client.get(
        f"/catalog/area-types/{area['area_type']['id']}/statuses", headers=auth_headers
    ).json()
    next_status = next(s for s in statuses if s["name"] != area["status"]["name"])

    response = client.patch(
        f"/projects/{project_id}/areas/{area['id']}",
        json={"status_id": next_status["id"]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"]["name"] == next_status["name"]

    status_change = next(
        entry for entry in fake_audit_log.entries if entry.action == "area.status_changed"
    )
    assert status_change.diff["from"] == area["status"]["name"]
    assert status_change.diff["to"] == next_status["name"]


def test_update_project_area_status_404_for_unknown_area(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = client.post(
        "/projects", json={"name": "Line 8 Retrofit"}, headers=auth_headers
    ).json()["id"]

    response = client.patch(
        f"/projects/{project_id}/areas/{uuid.uuid4()}",
        json={"status_id": str(uuid.uuid4())},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_timeline_is_chronological(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = client.post(
        "/projects", json={"name": "Line 9 Retrofit"}, headers=auth_headers
    ).json()["id"]
    client.post(
        f"/projects/{project_id}/labels",
        json={"name": "bug", "color": "#ff0000"},
        headers=auth_headers,
    )
    client.post(f"/projects/{project_id}/milestones", json={"title": "v1.0"}, headers=auth_headers)

    timeline = client.get(f"/projects/{project_id}/timeline", headers=auth_headers).json()
    occurred_ats = [entry["occurred_at"] for entry in timeline]
    assert occurred_ats == sorted(occurred_ats)
    assert [entry["action"] for entry in timeline] == [
        "project.created",
        "label.created",
        "milestone.created",
    ]
