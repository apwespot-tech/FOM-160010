"""Мероприятия: создание, представление, просмотр, изменение, удаление."""

from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Role
from tests.conftest import (
    ADMIN_PHONE,
    START,
    FakeClock,
    auth_header,
    create_event,
    event_payload,
    join,
    register,
    set_roles,
)

ORGANIZER = "+79991234567"
OTHER = "+79991234568"
THIRD = "+79991234569"
MISSING_ID = "00000000-0000-0000-0000-000000000000"
# Мероприятие скоро начнётся: часы можно сдвинуть за starts_at, пока access-токен (15 мин) жив
SOON = (START + timedelta(minutes=10)).isoformat()


def patch_event(client: TestClient, user: dict[str, Any], event_id: str, payload: Any) -> Any:
    return client.patch(f"/api/events/{event_id}", json=payload, headers=auth_header(user))


def get_event(client: TestClient, user: dict[str, Any], event_id: str) -> Any:
    return client.get(f"/api/events/{event_id}", headers=auth_header(user))


# --- создание и представление ---


def test_create_event(client: TestClient) -> None:
    organizer = register(client, ORGANIZER, name="Анна")

    response = client.post(
        "/api/events",
        json=event_payload(duration_minutes=120, min_age=16),
        headers=auth_header(organizer),
    )

    assert response.status_code == 201
    body = response.json()
    assert body.pop("id")
    assert body == {
        "title": "Настолки в антикафе",
        "description": "Играем в «Каркассон» и «Кодовые имена»",
        "place": "Антикафе «Циферблат»",
        "starts_at": "2026-11-01T12:00:00Z",
        "duration_minutes": 120,
        "created_at": "2026-10-31T12:00:00Z",
        "category": {"id": 1, "name": "Настольные игры"},
        "max_participants": 5,
        "min_age": 16,
        "organizer": {"id": organizer["id"], "name": "Анна", "photo_url": None, "telegram": None},
        "photos": [],
        "participants_count": 1,
        "free_places": 4,
        "is_full": False,
        "is_joined": True,
    }


def test_organizer_is_only_participant_after_create(client: TestClient) -> None:
    organizer = register(client, ORGANIZER, name="Анна")
    event = create_event(client, organizer)

    response = client.get(f"/api/events/{event['id']}/participants", headers=auth_header(organizer))

    assert response.json() == [
        {"id": organizer["id"], "name": "Анна", "photo_url": None, "telegram": None}
    ]


def test_full_event_representation(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    other = register(client, OTHER)
    event = create_event(client, organizer, max_participants=2)

    body = join(client, other, event["id"]).json()

    assert body["free_places"] == 0
    assert body["is_full"] is True


def test_starts_at_is_returned_in_utc(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    event = create_event(client, organizer, starts_at="2026-11-01T19:00:00+03:00")
    assert event["starts_at"] == "2026-11-01T16:00:00Z"


def test_create_bounds_of_limit(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    assert create_event(client, organizer, max_participants=2)["max_participants"] == 2
    assert create_event(client, organizer, max_participants=100)["max_participants"] == 100


def test_create_validation(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    for overrides in (
        {"max_participants": 1},
        {"max_participants": 101},
        {"min_age": 12},
        {"title": "   "},
        {"starts_at": "2026-12-01T19:00:00"},
    ):
        response = client.post(
            "/api/events", json=event_payload(**overrides), headers=auth_header(organizer)
        )
        assert response.status_code == 422, overrides


def test_create_with_unknown_category(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)

    response = client.post(
        "/api/events", json=event_payload(category_id=999), headers=auth_header(organizer)
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "category_not_found"


def test_create_in_past_or_now(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    for starts_at in (START - timedelta(hours=1), START):
        response = client.post(
            "/api/events",
            json=event_payload(starts_at=starts_at.isoformat()),
            headers=auth_header(organizer),
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "starts_at_in_past"


def test_create_requires_organizer_role(client: TestClient, db: Session) -> None:
    user = register(client, ORGANIZER)
    set_roles(db, user["id"], [Role.PARTICIPANT])

    response = client.post("/api/events", json=event_payload(), headers=auth_header(user))

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "forbidden"


# --- просмотр ---


def test_view_foreign_event(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    other = register(client, OTHER)
    event = create_event(client, organizer)

    response = get_event(client, other, event["id"])

    assert response.status_code == 200
    assert response.json()["is_joined"] is False
    assert set(response.json()["organizer"]) == {"id", "name", "photo_url", "telegram"}


# --- контакты организатора ---

PHOTO = "https://example.com/anna.jpg"


def test_organizer_telegram_hidden_from_outsider(client: TestClient) -> None:
    organizer = register(client, ORGANIZER, telegram="@anna_org", photo_url=PHOTO)
    outsider = register(client, OTHER)
    event = create_event(client, organizer)

    body = get_event(client, outsider, event["id"]).json()

    assert body["organizer"]["telegram"] is None
    assert body["organizer"]["photo_url"] == PHOTO
    assert "phone" not in body["organizer"]
    assert "email" not in body["organizer"]
    catalog_item = client.get("/api/events", headers=auth_header(outsider)).json()["items"][0]
    assert catalog_item["organizer"]["telegram"] is None


def test_organizer_telegram_for_participant_and_admin(client: TestClient) -> None:
    organizer = register(client, ORGANIZER, telegram="@anna_org")
    participant = register(client, OTHER)
    admin = register(client, ADMIN_PHONE)
    event = create_event(client, organizer)
    join(client, participant, event["id"])

    for viewer in (participant, admin, organizer):
        assert get_event(client, viewer, event["id"]).json()["organizer"]["telegram"] == (
            "@anna_org"
        )


def test_organizer_telegram_hidden_after_leave(client: TestClient) -> None:
    organizer = register(client, ORGANIZER, telegram="@anna_org")
    participant = register(client, OTHER)
    event = create_event(client, organizer)
    join(client, participant, event["id"])
    client.post(f"/api/events/{event['id']}/leave", headers=auth_header(participant))

    assert get_event(client, participant, event["id"]).json()["organizer"]["telegram"] is None


def test_view_past_event(client: TestClient, clock: FakeClock) -> None:
    organizer = register(client, ORGANIZER)
    event = create_event(client, organizer, starts_at=SOON)
    clock.advance(11 * 60)

    assert get_event(client, organizer, event["id"]).status_code == 200


def test_view_missing_event(client: TestClient) -> None:
    user = register(client, ORGANIZER)
    assert get_event(client, user, MISSING_ID).status_code == 404


# --- изменение ---


def test_author_updates_place(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    event = create_event(client, organizer)

    response = patch_event(client, organizer, event["id"], {"place": "Библиотека"})

    assert response.status_code == 200
    body = response.json()
    assert body["place"] == "Библиотека"
    assert body["title"] == event["title"]
    assert body["max_participants"] == event["max_participants"]


def test_update_several_fields_and_clear_duration(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    event = create_event(client, organizer, duration_minutes=90)

    response = patch_event(
        client,
        organizer,
        event["id"],
        {
            "duration_minutes": None,
            "category_id": 3,
            "min_age": 18,
            "starts_at": (START + timedelta(days=5)).isoformat(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["duration_minutes"] is None
    assert body["category"] == {"id": 3, "name": "Спорт"}
    assert body["min_age"] == 18
    assert body["starts_at"] == "2026-11-05T12:00:00Z"


def test_admin_updates_foreign_event(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    admin = register(client, ADMIN_PHONE)
    event = create_event(client, organizer)

    response = patch_event(client, admin, event["id"], {"title": "Новое"})

    assert response.status_code == 200
    assert response.json()["title"] == "Новое"


def test_participant_cannot_update(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    other = register(client, OTHER)
    event = create_event(client, organizer)
    join(client, other, event["id"])

    response = patch_event(client, other, event["id"], {"title": "Чужое"})

    assert response.status_code == 403
    assert get_event(client, organizer, event["id"]).json()["title"] == event["title"]


def test_update_missing_event(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    assert patch_event(client, organizer, MISSING_ID, {"title": "x"}).status_code == 404


def test_update_validation(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    event = create_event(client, organizer)

    past = patch_event(
        client, organizer, event["id"], {"starts_at": (START - timedelta(minutes=1)).isoformat()}
    )
    assert past.status_code == 422
    assert past.json()["detail"]["code"] == "starts_at_in_past"

    for payload in (
        {"organizer_id": organizer["id"]},
        {"id": MISSING_ID},
        {"title": None},
        {"max_participants": None},
        {"min_age": 15},
    ):
        assert patch_event(client, organizer, event["id"], payload).status_code == 422, payload

    unknown = patch_event(client, organizer, event["id"], {"category_id": 999})
    assert unknown.status_code == 422
    assert unknown.json()["detail"]["code"] == "category_not_found"


# --- лимит не ниже числа участников ---


def _event_with_participants(client: TestClient, count: int) -> tuple[dict[str, Any], str]:
    organizer = register(client, ORGANIZER)
    event = create_event(client, organizer, max_participants=10)
    for index in range(count - 1):
        participant = register(client, f"+7999000{index:04d}")
        assert join(client, participant, event["id"]).status_code == 200
    return organizer, event["id"]


def test_limit_below_participants(client: TestClient) -> None:
    organizer, event_id = _event_with_participants(client, 4)

    response = patch_event(client, organizer, event_id, {"max_participants": 3})

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "limit_below_participants"
    assert get_event(client, organizer, event_id).json()["max_participants"] == 10


def test_limit_equal_to_participants(client: TestClient) -> None:
    organizer, event_id = _event_with_participants(client, 4)

    response = patch_event(client, organizer, event_id, {"max_participants": 4})

    assert response.status_code == 200
    assert response.json()["is_full"] is True


# --- удаление ---


def test_author_deletes_event(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    other = register(client, OTHER)
    event = create_event(client, organizer)
    join(client, other, event["id"])

    response = client.delete(f"/api/events/{event['id']}", headers=auth_header(organizer))

    assert response.status_code == 204
    assert get_event(client, other, event["id"]).status_code == 404


def test_admin_deletes_foreign_event(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    admin = register(client, ADMIN_PHONE)
    event = create_event(client, organizer)

    response = client.delete(f"/api/events/{event['id']}", headers=auth_header(admin))

    assert response.status_code == 204


def test_participant_cannot_delete(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    other = register(client, OTHER)
    event = create_event(client, organizer)
    join(client, other, event["id"])

    response = client.delete(f"/api/events/{event['id']}", headers=auth_header(other))

    assert response.status_code == 403
    assert get_event(client, other, event["id"]).status_code == 200


def test_delete_missing_event(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    response = client.delete(f"/api/events/{MISSING_ID}", headers=auth_header(organizer))
    assert response.status_code == 404


# --- после начала ---


def test_update_at_start_moment(client: TestClient, clock: FakeClock) -> None:
    organizer = register(client, ORGANIZER)
    event = create_event(client, organizer, starts_at=SOON)
    clock.advance(10 * 60)  # ровно starts_at

    response = patch_event(client, organizer, event["id"], {"title": "Поздно"})

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "event_started"


def test_admin_cannot_delete_past_event(client: TestClient, clock: FakeClock) -> None:
    organizer = register(client, ORGANIZER)
    admin = register(client, ADMIN_PHONE)
    event = create_event(client, organizer, starts_at=SOON)
    clock.advance(11 * 60)

    response = client.delete(f"/api/events/{event['id']}", headers=auth_header(admin))

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "event_started"
    assert get_event(client, admin, event["id"]).status_code == 200


def test_rights_checked_before_start(client: TestClient, clock: FakeClock) -> None:
    organizer = register(client, ORGANIZER)
    other = register(client, THIRD)
    event = create_event(client, organizer, starts_at=SOON)
    clock.advance(11 * 60)

    assert patch_event(client, other, event["id"], {"title": "x"}).status_code == 403
