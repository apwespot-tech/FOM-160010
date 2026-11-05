"""Профиль: «О себе», город, интересы, счётчики и доступ участникам общих мероприятий."""

from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import (
    ADMIN_PHONE,
    START,
    FakeClock,
    auth_header,
    create_event,
    join,
    login,
    register,
)

ANNA = "+79991234567"
BORIS = "+79991234568"
VERA = "+79991234569"


def patch_own(client: TestClient, user: dict[str, Any], payload: dict[str, Any]) -> Any:
    return client.patch("/api/profile", json=payload, headers=auth_header(user))


def profile_of(client: TestClient, viewer: dict[str, Any], user_id: str) -> Any:
    return client.get(f"/api/profile/{user_id}", headers=auth_header(viewer))


def city_id(client: TestClient, user: dict[str, Any], name: str) -> int:
    items = client.get("/api/cities", headers=auth_header(user)).json()
    return int(next(c["id"] for c in items if c["name"] == name))


def code(response: Any) -> str:
    value: str = response.json()["detail"]["code"]
    return value


# --- новые поля ---


def test_about_boundary_and_line_breaks(client: TestClient) -> None:
    user = register(client, ANNA)
    text = ("Люблю настолки\nи прогулки " * 30)[:500]

    ok = patch_own(client, user, {"about": text})
    too_long = patch_own(client, user, {"about": "а" * 501})

    assert ok.status_code == 200
    assert ok.json()["about"] == text.strip()
    assert "\n" in ok.json()["about"]
    assert too_long.status_code == 422
    assert patch_own(client, user, {"about": "   "}).json()["about"] is None


def test_city_set_unknown_and_clear(client: TestClient) -> None:
    user = register(client, ANNA)
    moscow = city_id(client, user, "Москва")

    assert patch_own(client, user, {"city_id": moscow}).json()["city"] == {
        "id": moscow,
        "name": "Москва",
    }
    unknown = patch_own(client, user, {"city_id": 9999})
    assert unknown.status_code == 422
    assert code(unknown) == "city_not_found"
    assert patch_own(client, user, {"city_id": None}).json()["city"] is None


def test_interests_replace_order_and_clear(client: TestClient) -> None:
    user = register(client, ANNA)

    first = patch_own(client, user, {"interest_ids": [2, 1]})
    second = patch_own(client, user, {"interest_ids": [4]})
    cleared = patch_own(client, user, {"interest_ids": []})

    assert [(i["id"], i["name"]) for i in first.json()["interests"]] == [
        (1, "Настольные игры"),
        (2, "Прогулки"),
    ]
    assert first.json()["interests"][0]["icon"] == "pi-th-large"
    assert [i["id"] for i in second.json()["interests"]] == [4]
    assert cleared.json()["interests"] == []


def test_interests_validation(client: TestClient) -> None:
    user = register(client, ANNA)
    patch_own(client, user, {"interest_ids": [1]})

    unknown = patch_own(client, user, {"interest_ids": [1, 999]})
    repeated = patch_own(client, user, {"interest_ids": [2, 2]})
    null = patch_own(client, user, {"interest_ids": None})

    assert unknown.status_code == 422
    assert code(unknown) == "category_not_found"
    assert repeated.status_code == 422
    assert null.status_code == 422
    current = client.get("/api/profile", headers=auth_header(user)).json()
    assert [i["id"] for i in current["interests"]] == [1]


def test_photo_url_is_rejected(client: TestClient) -> None:
    user = register(client, ANNA)

    assert patch_own(client, user, {"photo_url": "https://example.com/a.png"}).status_code == 422


def test_admin_updates_new_fields(client: TestClient) -> None:
    user = register(client, ANNA)
    admin = register(client, ADMIN_PHONE)

    response = client.patch(
        f"/api/profile/{user['id']}",
        json={"about": "Модератор поправил", "interest_ids": [3]},
        headers=auth_header(admin),
    )

    assert response.status_code == 200
    assert response.json()["about"] == "Модератор поправил"
    assert [i["id"] for i in response.json()["interests"]] == [3]


# --- счётчики ---


def at(minutes: float) -> str:
    return (START + timedelta(minutes=minutes)).isoformat()


def test_stats(client: TestClient, clock: FakeClock) -> None:
    anna = register(client, ANNA)
    boris = register(client, BORIS)
    # Анна: одно своё (станет прошедшим) и два предстоящих своих
    create_event(client, anna, starts_at=at(5))
    create_event(client, anna, starts_at=at(60 * 24))
    create_event(client, anna, starts_at=at(60 * 48))
    # Борис организует: два станут прошедшими, одно предстоящее; Анна записана на все
    for minutes in (5, 6, 60 * 24):
        event = create_event(client, boris, starts_at=at(minutes))
        assert join(client, anna, event["id"]).status_code == 200
    # Ещё одно чужое, от которого Анна отказалась до начала
    left = create_event(client, boris, starts_at=at(7))
    join(client, anna, left["id"])
    client.post(f"/api/events/{left['id']}/leave", headers=auth_header(anna))

    clock.advance(6 * 60)  # мероприятие на +6 мин начинается ровно сейчас
    fresh = login(client, ANNA)

    stats = client.get("/api/profile", headers=auth_header(fresh)).json()["stats"]
    assert stats == {"organized_count": 3, "attended_count": 2}


# --- доступ к чужому профилю ---


def test_participant_and_organizer_see_each_other(client: TestClient) -> None:
    anna = register(client, ANNA, email="anna@example.com", telegram="@anna_org")
    boris = register(client, BORIS)
    event = create_event(client, anna)
    join(client, boris, event["id"])

    to_organizer = profile_of(client, boris, anna["id"])
    to_participant = profile_of(client, anna, boris["id"])

    assert to_organizer.status_code == 200
    assert to_organizer.json()["phone"] == ANNA
    assert to_organizer.json()["email"] == "anna@example.com"
    assert to_organizer.json()["birth_date"] == "2000-01-15"
    assert to_participant.status_code == 200


def test_two_participants_see_each_other(client: TestClient) -> None:
    anna = register(client, ANNA)
    boris = register(client, BORIS)
    vera = register(client, VERA)
    event = create_event(client, anna)
    join(client, boris, event["id"])
    join(client, vera, event["id"])

    assert profile_of(client, boris, vera["id"]).status_code == 200


def test_shared_past_event_keeps_access(client: TestClient, clock: FakeClock) -> None:
    anna = register(client, ANNA)
    boris = register(client, BORIS)
    event = create_event(client, anna, starts_at=at(5))
    join(client, boris, event["id"])
    clock.advance(10 * 60)
    fresh = login(client, BORIS)

    assert profile_of(client, fresh, anna["id"]).status_code == 200


def test_access_lost_after_leaving(client: TestClient) -> None:
    anna = register(client, ANNA)
    boris = register(client, BORIS)
    event = create_event(client, anna)
    join(client, boris, event["id"])
    client.post(f"/api/events/{event['id']}/leave", headers=auth_header(boris))

    response = profile_of(client, boris, anna["id"])

    assert response.status_code == 403


def test_no_shared_event_and_missing_user(client: TestClient) -> None:
    anna = register(client, ANNA)
    boris = register(client, BORIS)
    admin = register(client, ADMIN_PHONE)
    missing = "00000000-0000-0000-0000-000000000000"

    assert profile_of(client, boris, anna["id"]).status_code == 403
    assert profile_of(client, boris, missing).status_code == 403
    assert profile_of(client, admin, missing).status_code == 404


def test_shared_event_does_not_allow_editing(client: TestClient) -> None:
    anna = register(client, ANNA)
    boris = register(client, BORIS)
    event = create_event(client, anna)
    join(client, boris, event["id"])

    response = client.patch(
        f"/api/profile/{anna['id']}", json={"name": "Взлом"}, headers=auth_header(boris)
    )

    assert response.status_code == 403
    assert profile_of(client, boris, anna["id"]).json()["name"] == "Анна"
