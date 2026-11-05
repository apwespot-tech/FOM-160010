"""Справочник городов и город мероприятия."""

import threading
from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import (
    ADMIN_PHONE,
    FakeClock,
    auth_header,
    create_event,
    event_payload,
    login,
    register,
)

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


# --- изменение справочника администратором ---

ADMIN = ADMIN_PHONE
OTHER = "+79991234568"


def post_city(client: TestClient, user: dict[str, Any], name: Any) -> Any:
    return client.post("/api/cities", json={"name": name}, headers=auth_header(user))


def patch_city(client: TestClient, user: dict[str, Any], city: int, body: dict[str, Any]) -> Any:
    return client.patch(f"/api/cities/{city}", json=body, headers=auth_header(user))


def delete_city(client: TestClient, user: dict[str, Any], city: int) -> Any:
    return client.delete(f"/api/cities/{city}", headers=auth_header(user))


def test_dictionary_rights(client: TestClient) -> None:
    user = register(client, PHONE)
    draft = login(client, OTHER)
    moscow = city_id(client, user, "Москва")

    assert client.post("/api/cities", json={"name": "Тверь"}).status_code == 401
    assert client.delete(f"/api/cities/{moscow}").status_code == 401
    forbidden = post_city(client, user, "Тверь")
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["code"] == "forbidden"
    assert post_city(client, draft, "Тверь").json()["detail"]["code"] == "profile_incomplete"
    assert patch_city(client, user, moscow, {"name": "Мск"}).status_code == 403
    assert delete_city(client, user, moscow).status_code == 403
    assert "Тверь" not in {c["name"] for c in cities(client, user)}
    assert "Москва" in {c["name"] for c in cities(client, user)}


def test_admin_creates_city(client: TestClient) -> None:
    admin = register(client, ADMIN)

    response = post_city(client, admin, "  Тверь  ")

    assert response.status_code == 201
    assert response.json() == {"id": response.json()["id"], "name": "Тверь"}
    names = [c["name"] for c in cities(client, admin)]
    assert "Тверь" in names
    assert names == sorted(names)


def test_city_name_validation(client: TestClient) -> None:
    admin = register(client, ADMIN)

    assert post_city(client, admin, "Г" * 60).status_code == 201
    assert post_city(client, admin, "Д" * 61).status_code == 422
    assert post_city(client, admin, "   ").status_code == 422
    assert post_city(client, admin, None).status_code == 422
    extra = client.post("/api/cities", json={"name": "Тверь", "id": 1}, headers=auth_header(admin))
    assert extra.status_code == 422


def test_rename_city_visible_in_event_and_profile(client: TestClient) -> None:
    admin = register(client, ADMIN)
    tver = post_city(client, admin, "Тверь").json()["id"]
    event = create_event(client, admin, city_id=tver)
    client.patch("/api/profile", json={"city_id": tver}, headers=auth_header(admin))

    response = patch_city(client, admin, tver, {"name": "Тверь-на-Волге"})

    assert response.status_code == 200
    assert response.json()["name"] == "Тверь-на-Волге"
    got = client.get(f"/api/events/{event['id']}", headers=auth_header(admin)).json()
    assert got["city"]["name"] == "Тверь-на-Волге"
    profile = client.get("/api/profile", headers=auth_header(admin)).json()
    assert profile["city"]["name"] == "Тверь-на-Волге"


def test_rename_missing_or_cleared_city(client: TestClient) -> None:
    admin = register(client, ADMIN)
    moscow = city_id(client, admin, "Москва")

    assert patch_city(client, admin, 999999, {"name": "Тверь"}).status_code == 404
    assert patch_city(client, admin, moscow, {"name": None}).status_code == 422


def test_city_name_unique_case_insensitive(client: TestClient) -> None:
    admin = register(client, ADMIN)
    tver = post_city(client, admin, "Тверь").json()["id"]

    taken = post_city(client, admin, "москва")
    renamed_to_taken = patch_city(client, admin, tver, {"name": "МОСКВА"})
    own_case = patch_city(client, admin, tver, {"name": "ТВЕРЬ"})

    assert taken.status_code == 409
    assert taken.json()["detail"]["code"] == "city_name_taken"
    assert renamed_to_taken.status_code == 409
    assert own_case.status_code == 200
    assert own_case.json()["name"] == "ТВЕРЬ"


def test_concurrent_city_create(client: TestClient) -> None:
    admin = register(client, ADMIN)
    barrier = threading.Barrier(2)
    statuses: list[int] = []

    def worker() -> None:
        barrier.wait()
        statuses.append(post_city(client, admin, "Тверь").status_code)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(statuses) == [201, 409]
    assert [c["name"] for c in cities(client, admin)].count("Тверь") == 1


def test_delete_city_clears_profiles(client: TestClient) -> None:
    admin = register(client, ADMIN)
    user = register(client, PHONE)
    tver = post_city(client, admin, "Тверь").json()["id"]
    client.patch("/api/profile", json={"city_id": tver}, headers=auth_header(user))

    response = delete_city(client, admin, tver)

    assert response.status_code == 204
    assert "Тверь" not in {c["name"] for c in cities(client, admin)}
    assert client.get("/api/profile", headers=auth_header(user)).json()["city"] is None
    assert delete_city(client, admin, tver).status_code == 404


def test_city_with_past_event_cannot_be_deleted(client: TestClient, clock: FakeClock) -> None:
    admin = register(client, ADMIN)
    tver = post_city(client, admin, "Тверь").json()["id"]
    create_event(client, admin, city_id=tver)
    clock.advance(3 * 24 * 3600)
    admin = login(client, ADMIN)  # access-токен за это время истёк

    response = delete_city(client, admin, tver)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "city_in_use"
    assert "Тверь" in {c["name"] for c in cities(client, admin)}
