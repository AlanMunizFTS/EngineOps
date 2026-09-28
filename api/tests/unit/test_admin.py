from fastapi.testclient import TestClient


def test_non_admin_cannot_list_users(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/admin/users", headers=auth_headers)
    assert response.status_code == 403


def test_admin_can_list_users(
    client: TestClient, admin_auth_headers: dict[str, str], admin_user
) -> None:
    response = client.get("/admin/users", headers=admin_auth_headers)
    assert response.status_code == 200
    emails = {u["email"] for u in response.json()}
    assert admin_user.email in emails


def test_admin_can_create_user(client: TestClient, admin_auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/admin/users",
        json={
            "email": "newperson@martinrea.com",
            "password": "supersecret",
            "full_name": "New Person",
        },
        headers=admin_auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "newperson@martinrea.com"
    assert body["roles"] == []


def test_admin_can_create_another_admin(
    client: TestClient, admin_auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/admin/users",
        json={
            "email": "secondadmin@martinrea.com",
            "password": "supersecret",
            "full_name": "Second Admin",
            "is_admin": True,
        },
        headers=admin_auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["roles"] == ["admin"]


def test_non_admin_cannot_create_user(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/admin/users",
        json={"email": "x@martinrea.com", "password": "supersecret", "full_name": "X"},
        headers=auth_headers,
    )
    assert response.status_code == 403


def test_admin_can_update_user_fields(
    client: TestClient,
    admin_auth_headers: dict[str, str],
    current_user,
) -> None:
    response = client.patch(
        f"/admin/users/{current_user.id}",
        json={
            "email": "updated@example.com",
            "full_name": "Updated Name",
            "password": "newpassword",
            "is_active": False,
            "roles": ["engineer", "viewer"],
        },
        headers=admin_auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["email"] == "updated@example.com"
    assert response.json()["full_name"] == "Updated Name"
    assert response.json()["is_active"] is False
    assert response.json()["roles"] == ["engineer", "viewer"]


def test_non_admin_cannot_update_users(
    client: TestClient,
    auth_headers: dict[str, str],
    current_user,
) -> None:
    response = client.patch(
        f"/admin/users/{current_user.id}",
        json={"full_name": "Updated Name"},
        headers=auth_headers,
    )

    assert response.status_code == 403


def test_admin_cannot_remove_own_admin_role(
    client: TestClient,
    admin_auth_headers: dict[str, str],
    admin_user,
) -> None:
    response = client.patch(
        f"/admin/users/{admin_user.id}",
        json={"roles": []},
        headers=admin_auth_headers,
    )

    assert response.status_code == 400


def test_create_user_rejects_duplicate_email(
    client: TestClient, admin_auth_headers: dict[str, str], current_user
) -> None:
    response = client.post(
        "/admin/users",
        json={"email": current_user.email, "password": "supersecret", "full_name": "Dupe"},
        headers=admin_auth_headers,
    )
    assert response.status_code == 409


def test_admin_can_delete_user(
    client: TestClient, admin_auth_headers: dict[str, str], current_user
) -> None:
    response = client.delete(f"/admin/users/{current_user.id}", headers=admin_auth_headers)
    assert response.status_code == 204

    listing = client.get("/admin/users", headers=admin_auth_headers).json()
    assert current_user.id not in {u["id"] for u in listing}


def test_admin_cannot_delete_self(
    client: TestClient, admin_auth_headers: dict[str, str], admin_user
) -> None:
    response = client.delete(f"/admin/users/{admin_user.id}", headers=admin_auth_headers)
    assert response.status_code == 400


def test_delete_user_404_for_unknown_id(
    client: TestClient, admin_auth_headers: dict[str, str]
) -> None:
    response = client.delete(
        "/admin/users/00000000-0000-0000-0000-000000000000", headers=admin_auth_headers
    )
    assert response.status_code == 404


def test_login_with_local_part_only(
    client: TestClient,
    fake_user_repository,
    auth_headers: dict[str, str],
) -> None:
    client.post(
        "/auth/users",
        json={
            "email": "jdoe@martinrea.com",
            "password": "supersecret",
            "full_name": "J Doe",
        },
        headers=auth_headers,
    )
    response = client.post("/auth/login", json={"email": "jdoe", "password": "supersecret"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_with_local_part_does_not_affect_other_domains(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    client.post(
        "/auth/users",
        json={
            "email": "jdoe@othercompany.com",
            "password": "supersecret",
            "full_name": "J Doe",
        },
        headers=auth_headers,
    )
    # bare "jdoe" resolves to jdoe@martinrea.com, not jdoe@othercompany.com
    response = client.post("/auth/login", json={"email": "jdoe", "password": "supersecret"})
    assert response.status_code == 401

    full_email_response = client.post(
        "/auth/login", json={"email": "jdoe@othercompany.com", "password": "supersecret"}
    )
    assert full_email_response.status_code == 200
