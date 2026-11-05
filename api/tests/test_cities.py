"""Справочник городов и город мероприятия."""

from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import auth_header, create_event, event_payload, login, register

PHONE = "+79991234567"


def cities(client: TestClient, user: dict[str, Any]) -> list[dict[str, Any]]:
    response = client.get("/api/cities", headers=auth_header(user))
    assert response.status_code == 200
    result: list[dict[str, Any]] = response.json()
    return result


def city_id(client: TestClient, user: dict[str, Any], name: str) -> int:
    return next(c["id"] for c in cities(client, user) if c["name"] == name)


def test_cities_sorted_by_name(client: TestClient) -> None:
    user = register(client, PHONE)

    items = cities(client, user)

    names = [c["name"] for c in items]
    assert names == sorted(names)
    assert {"Москва", "Санкт-Петербург"} <= set(names)
    assert all(set(c) == {"id", "name"} for c in items)


def test_cities_access(client: TestClient) -> None:
    draft = login(client, PHONE)

    assert client.get("/api/cities").status_code == 401
    response = client.get("/api/cities", headers=auth_header(draft))
    assert response.status_code == 200
    assert "Москва" in {c["name"] for c in response.json()}


def test_event_requires_existing_city(client: TestClient) -> None:
    user = register(client, PHONE)
    without_city = event_payload()
    del without_city["city_id"]

    missing = client.post("/api/events", json=without_city, headers=auth_header(user))
    unknown = client.post(
        "/api/events", json=event_payload(city_id=9999), headers=auth_header(user)
    )

    assert missing.status_code == 422
    assert unknown.status_code == 422
    assert unknown.json()["detail"]["code"] == "city_not_found"


def test_event_city_can_be_changed_but_not_cleared(client: TestClient) -> None:
    user = register(client, PHONE)
    kazan = city_id(client, user, "Казань")
    event = create_event(client, user)
    assert event["city"]["name"] == "Москва"

    changed = client.patch(
        f"/api/events/{event['id']}", json={"city_id": kazan}, headers=auth_header(user)
    )
    cleared = client.patch(
        f"/api/events/{event['id']}", json={"city_id": None}, headers=auth_header(user)
    )
    unknown = client.patch(
        f"/api/events/{event['id']}", json={"city_id": 9999}, headers=auth_header(user)
    )

    assert changed.status_code == 200
    assert changed.json()["city"] == {"id": kazan, "name": "Казань"}
    assert cleared.status_code == 422
    assert unknown.status_code == 422
    assert unknown.json()["detail"]["code"] == "city_not_found"
