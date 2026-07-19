from fastapi.testclient import TestClient


def test_recent_activity_spans_projects_newest_first(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    first_project = client.post(
        "/projects", json={"name": "Line 4 Retrofit"}, headers=auth_headers
    ).json()
    second_project = client.post(
        "/projects", json={"name": "Line 5 Retrofit"}, headers=auth_headers
    ).json()

    activity = client.get("/activity", headers=auth_headers).json()

    assert [item["project_name"] for item in activity] == [
        second_project["name"],
        first_project["name"],
    ]
    assert all(item["action"] == "project.created" for item in activity)


def test_recent_activity_respects_limit(client: TestClient, auth_headers: dict[str, str]) -> None:
    for i in range(3):
        client.post("/projects", json={"name": f"Project {i}"}, headers=auth_headers)

    activity = client.get("/activity", params={"limit": 2}, headers=auth_headers).json()
    assert len(activity) == 2
