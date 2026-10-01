import uuid

from fastapi.testclient import TestClient


def _create_project(client: TestClient, auth_headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Endforms"}, headers=auth_headers)
    return response.json()["id"]


def test_create_folder(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)

    response = client.post(
        f"/projects/{project_id}/tree",
        json={"node_type": "folder", "name": "Presentations"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["project_id"] == project_id
    assert body["node_type"] == "folder"
    assert body["name"] == "Presentations"
    assert body["parent_id"] is None
    assert body["url"] is None


def test_create_link_requires_url(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)

    response = client.post(
        f"/projects/{project_id}/tree",
        json={"node_type": "link", "name": "Kickoff deck"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_folder_rejects_url(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)

    response = client.post(
        f"/projects/{project_id}/tree",
        json={
            "node_type": "folder",
            "name": "Presentations",
            "url": "https://example.com/deck",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_link_inside_folder(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    folder = client.post(
        f"/projects/{project_id}/tree",
        json={"node_type": "folder", "name": "Presentations"},
        headers=auth_headers,
    ).json()

    response = client.post(
        f"/projects/{project_id}/tree",
        json={
            "node_type": "link",
            "name": "Kickoff deck",
            "url": "https://example.com/kickoff.pptx",
            "parent_id": folder["id"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["parent_id"] == folder["id"]
    assert body["url"] == "https://example.com/kickoff.pptx"


def test_create_node_404_for_unknown_parent(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)

    response = client.post(
        f"/projects/{project_id}/tree",
        json={
            "node_type": "link",
            "name": "Kickoff deck",
            "url": "https://example.com/kickoff.pptx",
            "parent_id": str(uuid.uuid4()),
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_create_node_404_for_unknown_project(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        f"/projects/{uuid.uuid4()}/tree",
        json={"node_type": "folder", "name": "Presentations"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_list_file_tree_returns_all_nodes(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    client.post(
        f"/projects/{project_id}/tree",
        json={"node_type": "folder", "name": "Presentations"},
        headers=auth_headers,
    )
    client.post(
        f"/projects/{project_id}/tree",
        json={"node_type": "link", "name": "Spec", "url": "https://example.com/spec"},
        headers=auth_headers,
    )

    nodes = client.get(f"/projects/{project_id}/tree", headers=auth_headers).json()
    assert {node["name"] for node in nodes} == {"Presentations", "Spec", "SCOPE.md"}


def test_delete_folder_cascades_to_children(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    folder = client.post(
        f"/projects/{project_id}/tree",
        json={"node_type": "folder", "name": "Presentations"},
        headers=auth_headers,
    ).json()
    client.post(
        f"/projects/{project_id}/tree",
        json={
            "node_type": "link",
            "name": "Kickoff deck",
            "url": "https://example.com/kickoff.pptx",
            "parent_id": folder["id"],
        },
        headers=auth_headers,
    )

    response = client.delete(f"/projects/{project_id}/tree/{folder['id']}", headers=auth_headers)
    assert response.status_code == 204

    nodes = client.get(f"/projects/{project_id}/tree", headers=auth_headers).json()
    assert {node["name"] for node in nodes} == {"SCOPE.md"}


def test_delete_node_404_for_unknown_node(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)

    response = client.delete(f"/projects/{project_id}/tree/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_create_project_seeds_scope_md(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)

    nodes = client.get(f"/projects/{project_id}/tree", headers=auth_headers).json()
    scope = next(node for node in nodes if node["name"] == "SCOPE.md")
    assert scope["node_type"] == "file"
    assert scope["parent_id"] is None
    assert scope["content"]


def test_create_file_with_content(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)

    response = client.post(
        f"/projects/{project_id}/tree",
        json={"node_type": "file", "name": "notes.md", "content": "# Notes"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["node_type"] == "file"
    assert body["content"] == "# Notes"
    assert body["url"] is None


def test_create_link_rejects_content(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)

    response = client.post(
        f"/projects/{project_id}/tree",
        json={
            "node_type": "link",
            "name": "Spec",
            "url": "https://example.com/spec",
            "content": "should not be allowed",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_update_file_content(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    node = client.post(
        f"/projects/{project_id}/tree",
        json={"node_type": "file", "name": "notes.md", "content": "draft"},
        headers=auth_headers,
    ).json()

    response = client.patch(
        f"/projects/{project_id}/tree/{node['id']}",
        json={"content": "final"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["content"] == "final"


def test_update_content_400_for_non_file_node(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    folder = client.post(
        f"/projects/{project_id}/tree",
        json={"node_type": "folder", "name": "Presentations"},
        headers=auth_headers,
    ).json()

    response = client.patch(
        f"/projects/{project_id}/tree/{folder['id']}",
        json={"content": "should fail"},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_update_content_404_for_unknown_node(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)

    response = client.patch(
        f"/projects/{project_id}/tree/{uuid.uuid4()}",
        json={"content": "irrelevant"},
        headers=auth_headers,
    )
    assert response.status_code == 404
