import uuid
from decimal import Decimal

from fastapi.testclient import TestClient


def _create_project(client: TestClient, auth_headers: dict[str, str]) -> str:
    response = client.post("/projects", json={"name": "Stamping Cell 3"}, headers=auth_headers)
    return response.json()["id"]


def _create_part_number(client: TestClient, project_id: str, auth_headers: dict, name: str) -> str:
    return client.post(
        f"/projects/{project_id}/part-numbers", json={"name": name}, headers=auth_headers
    ).json()["id"]


def _create_condition(client: TestClient, project_id: str, auth_headers: dict, name: str) -> str:
    return client.post(
        f"/projects/{project_id}/piece-conditions", json={"name": name}, headers=auth_headers
    ).json()["id"]


def _create_location(client: TestClient, project_id: str, auth_headers: dict, name: str) -> str:
    return client.post(
        f"/projects/{project_id}/piece-locations", json={"name": name}, headers=auth_headers
    ).json()["id"]


def test_part_number_create_and_list(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)

    created = client.post(
        f"/projects/{project_id}/part-numbers", json={"name": "Mushroom"}, headers=auth_headers
    )
    assert created.status_code == 201
    assert created.json()["name"] == "Mushroom"

    listed = client.get(f"/projects/{project_id}/part-numbers", headers=auth_headers)
    assert [p["name"] for p in listed.json()] == ["Mushroom"]


def test_piece_condition_and_location_create_and_list(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)

    _create_condition(client, project_id, auth_headers, "Split")
    conditions = client.get(f"/projects/{project_id}/piece-conditions", headers=auth_headers)
    assert [c["name"] for c in conditions.json()] == ["Split"]

    _create_location(client, project_id, auth_headers, "Arteaga")
    locations = client.get(f"/projects/{project_id}/piece-locations", headers=auth_headers)
    assert [loc["name"] for loc in locations.json()] == ["Arteaga"]


def test_measurement_type_scoped_to_condition_and_part_number(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    part_number_id = _create_part_number(client, project_id, auth_headers, "Mushroom")
    condition_id = _create_condition(client, project_id, auth_headers, "Split")

    response = client.post(
        f"/projects/{project_id}/measurement-types",
        json={
            "name": "Split Width",
            "unit": "mm",
            "condition_id": condition_id,
            "part_number_id": part_number_id,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["condition_id"] == condition_id
    assert body["part_number_id"] == part_number_id
    assert body["status"] is None


def test_measurement_type_scoped_to_status(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    part_number_id = _create_part_number(client, project_id, auth_headers, "Mushroom")

    response = client.post(
        f"/projects/{project_id}/measurement-types",
        json={
            "name": "Split Width",
            "unit": "mm",
            "part_number_id": part_number_id,
            "status": "nok",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["part_number_id"] == part_number_id
    assert body["condition_id"] is None
    assert body["status"] == "nok"

    listed = client.get(f"/projects/{project_id}/measurement-types", headers=auth_headers).json()
    assert listed[0]["status"] == "nok"


def test_update_measurement_type_changes_scope(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    part_number_id = _create_part_number(client, project_id, auth_headers, "Mushroom")
    condition_id = _create_condition(client, project_id, auth_headers, "Split")
    measurement_type = client.post(
        f"/projects/{project_id}/measurement-types",
        json={"name": "Split Width", "unit": "mm"},
        headers=auth_headers,
    ).json()

    response = client.patch(
        f"/measurement-types/{measurement_type['id']}",
        json={
            "name": "Split Width",
            "unit": "microns",
            "part_number_id": part_number_id,
            "condition_id": condition_id,
            "status": "nok",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["unit"] == "microns"
    assert body["part_number_id"] == part_number_id
    assert body["condition_id"] == condition_id
    assert body["status"] == "nok"


def test_update_measurement_type_404_for_unknown_id(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.patch(
        f"/measurement-types/{uuid.uuid4()}",
        json={"name": "X", "unit": "mm"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_delete_measurement_type(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    part_number_id = _create_part_number(client, project_id, auth_headers, "Mushroom")
    measurement_type = client.post(
        f"/projects/{project_id}/measurement-types",
        json={"name": "External Diameter", "unit": "mm"},
        headers=auth_headers,
    ).json()
    piece = client.post(
        f"/projects/{project_id}/pieces",
        json={"part_number_id": part_number_id, "status": "ok"},
        headers=auth_headers,
    ).json()[0]
    client.put(
        f"/pieces/{piece['id']}/measurements/{measurement_type['id']}",
        json={"value": "5.0"},
        headers=auth_headers,
    )

    response = client.delete(
        f"/measurement-types/{measurement_type['id']}", headers=auth_headers
    )
    assert response.status_code == 204

    listed = client.get(f"/projects/{project_id}/measurement-types", headers=auth_headers).json()
    assert listed == []


def test_delete_measurement_type_404_for_unknown_id(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.delete(f"/measurement-types/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_create_pieces_with_quantity_produces_distinct_hex_tracking_numbers(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    part_number_id = _create_part_number(client, project_id, auth_headers, "Mushroom")

    response = client.post(
        f"/projects/{project_id}/pieces",
        json={"part_number_id": part_number_id, "status": "ok", "quantity": 5},
        headers=auth_headers,
    )
    assert response.status_code == 201
    pieces = response.json()
    assert len(pieces) == 5
    tracking_numbers = [p["tracking_number"] for p in pieces]
    assert len(set(tracking_numbers)) == 5
    for number in tracking_numbers:
        assert len(number) == 6
        assert number == number.upper()
        int(number, 16)  # raises if not valid hex


def test_piece_create_404_for_unknown_project(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        f"/projects/{uuid.uuid4()}/pieces",
        json={"part_number_id": str(uuid.uuid4()), "status": "ok"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_measurement_upsert_respects_one_value_per_type(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    part_number_id = _create_part_number(client, project_id, auth_headers, "Mushroom")
    measurement_type_id = client.post(
        f"/projects/{project_id}/measurement-types",
        json={"name": "External Diameter", "unit": "mm"},
        headers=auth_headers,
    ).json()["id"]
    piece = client.post(
        f"/projects/{project_id}/pieces",
        json={"part_number_id": part_number_id, "status": "ok"},
        headers=auth_headers,
    ).json()[0]

    first = client.put(
        f"/pieces/{piece['id']}/measurements/{measurement_type_id}",
        json={"value": "12.5"},
        headers=auth_headers,
    )
    assert first.status_code == 200
    assert len(first.json()["measurements"]) == 1
    assert Decimal(str(first.json()["measurements"][0]["value"])) == Decimal("12.5")

    second = client.put(
        f"/pieces/{piece['id']}/measurements/{measurement_type_id}",
        json={"value": "13.0"},
        headers=auth_headers,
    )
    assert second.status_code == 200
    measurements = second.json()["measurements"]
    assert len(measurements) == 1
    assert Decimal(str(measurements[0]["value"])) == Decimal("13.0")
    assert measurements[0]["name"] == "External Diameter"
    assert measurements[0]["unit"] == "mm"


def test_combined_filter_mushroom_nok_split_width_over_threshold(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    mushroom_id = _create_part_number(client, project_id, auth_headers, "Mushroom")
    double_flare_id = _create_part_number(client, project_id, auth_headers, "Double Flare")
    split_id = _create_condition(client, project_id, auth_headers, "Split")
    collapse_id = _create_condition(client, project_id, auth_headers, "Collapse")
    width_type_id = client.post(
        f"/projects/{project_id}/measurement-types",
        json={"name": "Split Width", "unit": "mm", "condition_id": split_id},
        headers=auth_headers,
    ).json()["id"]

    def register(part_number_id: str, status: str, condition_ids: list[str]) -> dict:
        return client.post(
            f"/projects/{project_id}/pieces",
            json={
                "part_number_id": part_number_id,
                "status": status,
                "condition_ids": condition_ids,
            },
            headers=auth_headers,
        ).json()[0]

    matching = register(mushroom_id, "nok", [split_id])
    client.put(
        f"/pieces/{matching['id']}/measurements/{width_type_id}",
        json={"value": "0.5"},
        headers=auth_headers,
    )

    below_threshold = register(mushroom_id, "nok", [split_id])
    client.put(
        f"/pieces/{below_threshold['id']}/measurements/{width_type_id}",
        json={"value": "0.1"},
        headers=auth_headers,
    )

    wrong_condition = register(mushroom_id, "nok", [collapse_id])
    wrong_part_number = register(double_flare_id, "nok", [split_id])
    client.put(
        f"/pieces/{wrong_part_number['id']}/measurements/{width_type_id}",
        json={"value": "0.9"},
        headers=auth_headers,
    )
    wrong_status = register(mushroom_id, "ok", [split_id])

    response = client.get(
        f"/projects/{project_id}/pieces",
        params={
            "part_number_id": mushroom_id,
            "status": "nok",
            "condition_id": [split_id],
            "measurement_type_id": width_type_id,
            "measurement_min": "0.3",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    result_ids = {p["id"] for p in response.json()}
    assert result_ids == {matching["id"]}
    assert below_threshold["id"] not in result_ids
    assert wrong_condition["id"] not in result_ids
    assert wrong_part_number["id"] not in result_ids
    assert wrong_status["id"] not in result_ids


def test_update_piece_replaces_conditions_and_location(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    project_id = _create_project(client, auth_headers)
    part_number_id = _create_part_number(client, project_id, auth_headers, "Mushroom")
    split_id = _create_condition(client, project_id, auth_headers, "Split")
    hit_id = _create_condition(client, project_id, auth_headers, "Hit")
    location_id = _create_location(client, project_id, auth_headers, "Lab")
    piece = client.post(
        f"/projects/{project_id}/pieces",
        json={"part_number_id": part_number_id, "status": "nok", "condition_ids": [split_id]},
        headers=auth_headers,
    ).json()[0]

    response = client.patch(
        f"/pieces/{piece['id']}",
        json={
            "status": "nok",
            "location_id": location_id,
            "notes": "moved to lab",
            "condition_ids": [hit_id],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["location_id"] == location_id
    assert body["notes"] == "moved to lab"
    assert [c["id"] for c in body["conditions"]] == [hit_id]


def test_update_piece_changes_status(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _create_project(client, auth_headers)
    part_number_id = _create_part_number(client, project_id, auth_headers, "Mushroom")
    piece = client.post(
        f"/projects/{project_id}/pieces",
        json={"part_number_id": part_number_id, "status": "ok"},
        headers=auth_headers,
    ).json()[0]

    response = client.patch(
        f"/pieces/{piece['id']}",
        json={"status": "nok", "location_id": None, "notes": None, "condition_ids": []},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["overall_status"] == "nok"
