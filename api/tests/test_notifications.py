"""Уведомления: создание при действиях с мероприятием, напоминание об окне отзывов, API."""

import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import EventParticipant, Notification, NotificationType
from app.services import notification_service
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
from tests.test_dictionary_races import run_together

ORGANIZER = "+79991234567"
ANNA = "+79991234568"
OLEG = "+79991234569"
DRAFT = "+79991234570"

STARTS_AT = START + timedelta(days=1)
REVIEWS_OPEN = STARTS_AT + timedelta(hours=24)
REVIEWS_CLOSE = STARTS_AT + timedelta(days=8)

User = dict[str, Any]


def notifications(client: TestClient, user: User) -> dict[str, Any]:
    response = client.get("/api/notifications", headers=auth_header(user))
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def items(client: TestClient, user: User) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = notifications(client, user)["items"]
    return result


def types(client: TestClient, user: User) -> list[str]:
    return [item["type"] for item in items(client, user)]


def patch_event(client: TestClient, user: User, event_id: str, **fields: Any) -> Any:
    return client.patch(f"/api/events/{event_id}", json=fields, headers=auth_header(user))


def mark_read(client: TestClient, user: User, up_to: str) -> Any:
    return client.post("/api/notifications/read", json={"up_to": up_to}, headers=auth_header(user))


@pytest.fixture
def organizer(client: TestClient) -> User:
    return register(client, ORGANIZER, name="Ира")


@pytest.fixture
def anna(client: TestClient) -> User:
    return register(client, ANNA, name="Анна")


@pytest.fixture
def oleg(client: TestClient) -> User:
    return register(client, OLEG, name="Олег")


@pytest.fixture
def event(client: TestClient, organizer: User) -> dict[str, Any]:
    return create_event(client, organizer, title="Мафия", starts_at=STARTS_AT.isoformat())


@pytest.fixture
def joined(
    client: TestClient, event: dict[str, Any], anna: User, oleg: User, clock: FakeClock
) -> dict[str, Any]:
    """Мероприятие, на которое записаны Анна и Олег (организатор получил два уведомления)."""
    for user in (anna, oleg):
        assert join(client, user, event["id"]).status_code == 200
        clock.advance(1)
    return event


# --- изменение мероприятия ---


def test_event_change_notifies_participants_except_actor(
    client: TestClient, organizer: User, anna: User, oleg: User, joined: dict[str, Any]
) -> None:
    third = register(client, "+79991234571", name="Пётр")
    assert join(client, third, joined["id"]).status_code == 200
    organizer_before = types(client, organizer)

    response = patch_event(
        client,
        organizer,
        joined["id"],
        place="Новое место",
        starts_at=(STARTS_AT + timedelta(hours=2)).isoformat(),
    )

    assert response.status_code == 200, response.text
    for user in (anna, oleg, third):
        [latest, *_] = items(client, user)
        assert latest["type"] == "event_changed"
        assert latest["changed_fields"] == ["starts_at", "place"]
        assert latest["participant"] is None
        assert latest["event"] == {"id": joined["id"], "title": "Мафия"}
    assert types(client, organizer) == organizer_before


def test_event_change_of_other_fields_does_not_notify(
    client: TestClient, organizer: User, anna: User, joined: dict[str, Any]
) -> None:
    response = patch_event(
        client, organizer, joined["id"], description="Новое описание", max_participants=6
    )

    assert response.status_code == 200
    assert "event_changed" not in types(client, anna)


def test_event_change_with_same_value_does_not_notify(
    client: TestClient, organizer: User, anna: User, joined: dict[str, Any]
) -> None:
    response = patch_event(client, organizer, joined["id"], place=joined["place"])

    assert response.status_code == 200
    assert "event_changed" not in types(client, anna)


def test_event_title_change_uses_new_title(
    client: TestClient, organizer: User, anna: User, joined: dict[str, Any]
) -> None:
    assert patch_event(client, organizer, joined["id"], title="Мафия в пятницу").status_code == 200

    [latest, *_] = items(client, anna)
    assert latest["changed_fields"] == ["title"]
    assert latest["event"]["title"] == "Мафия в пятницу"


def test_event_change_fields_follow_fixed_order(
    client: TestClient, organizer: User, anna: User, joined: dict[str, Any]
) -> None:
    response = patch_event(
        client,
        organizer,
        joined["id"],
        title="Мафия 2",
        place="Другое место",
        duration_minutes=90,
        city_id=2,
    )

    assert response.status_code == 200, response.text
    [latest, *_] = items(client, anna)
    assert latest["changed_fields"] == ["duration_minutes", "city_id", "place", "title"]


def test_admin_change_notifies_organizer(
    client: TestClient, organizer: User, anna: User, joined: dict[str, Any]
) -> None:
    admin = register(client, ADMIN_PHONE, name="Админ")

    response = patch_event(
        client, admin, joined["id"], starts_at=(STARTS_AT + timedelta(hours=1)).isoformat()
    )

    assert response.status_code == 200
    assert items(client, organizer)[0]["type"] == "event_changed"
    assert items(client, anna)[0]["type"] == "event_changed"
    assert items(client, admin) == []


def test_rejected_change_does_not_notify(
    client: TestClient, organizer: User, anna: User, oleg: User, joined: dict[str, Any]
) -> None:
    # Записаны трое: лимит 2 меньше числа участников
    response = patch_event(client, organizer, joined["id"], place="Другое", max_participants=2)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "limit_below_participants"
    assert "event_changed" not in types(client, anna)


def test_change_without_other_participants_creates_nothing(
    client: TestClient, organizer: User, event: dict[str, Any], db: Session
) -> None:
    response = patch_event(
        client, organizer, event["id"], starts_at=(STARTS_AT + timedelta(hours=1)).isoformat()
    )

    assert response.status_code == 200
    assert db.scalar(select(func.count()).select_from(Notification)) == 0


# --- удаление мероприятия ---


def test_event_delete_notifies_participants_with_title(
    client: TestClient, organizer: User, anna: User, oleg: User, joined: dict[str, Any]
) -> None:
    organizer_before = types(client, organizer)

    response = client.delete(f"/api/events/{joined['id']}", headers=auth_header(organizer))

    assert response.status_code == 204
    for user in (anna, oleg):
        [latest, *_] = items(client, user)
        assert latest["type"] == "event_deleted"
        assert latest["event"] == {"id": None, "title": "Мафия"}
    assert types(client, organizer) == organizer_before


def test_admin_delete_notifies_organizer(
    client: TestClient, organizer: User, joined: dict[str, Any]
) -> None:
    admin = register(client, ADMIN_PHONE, name="Админ")

    assert (
        client.delete(f"/api/events/{joined['id']}", headers=auth_header(admin)).status_code == 204
    )

    assert items(client, organizer)[0]["type"] == "event_deleted"


def test_rejected_delete_does_not_notify(
    client: TestClient, organizer: User, anna: User, clock: FakeClock
) -> None:
    # Токены живут 15 минут: мероприятие начинается раньше, чем они истекут
    soon = create_event(client, organizer, starts_at=(START + timedelta(minutes=10)).isoformat())
    assert join(client, anna, soon["id"]).status_code == 200
    clock.advance(10 * 60)

    response = client.delete(f"/api/events/{soon['id']}", headers=auth_header(organizer))

    assert response.json()["detail"]["code"] == "event_started"
    assert "event_deleted" not in types(client, anna)


def test_notifications_survive_event_delete(
    client: TestClient, organizer: User, anna: User, joined: dict[str, Any]
) -> None:
    assert (
        client.delete(f"/api/events/{joined['id']}", headers=auth_header(organizer)).status_code
        == 204
    )

    joined_items = [i for i in items(client, organizer) if i["type"] == "participant_joined"]
    assert len(joined_items) == 2
    assert all(i["event"] == {"id": None, "title": "Мафия"} for i in joined_items)


# --- исключение ---


def remove(client: TestClient, actor: User, event_id: str, user_id: str) -> Any:
    return client.post(
        f"/api/events/{event_id}/participants/{user_id}/remove", headers=auth_header(actor)
    )


def test_organizer_removes_participant(
    client: TestClient, organizer: User, anna: User, joined: dict[str, Any]
) -> None:
    organizer_before = types(client, organizer)

    assert remove(client, organizer, joined["id"], anna["id"]).status_code == 200

    [latest, *_] = items(client, anna)
    assert latest["type"] == "participant_removed"
    assert latest["participant"] == {"id": anna["id"], "name": "Анна"}
    assert types(client, organizer) == organizer_before


def test_admin_removes_participant(
    client: TestClient, organizer: User, anna: User, joined: dict[str, Any]
) -> None:
    admin = register(client, ADMIN_PHONE, name="Админ")

    assert remove(client, admin, joined["id"], anna["id"]).status_code == 200

    for user in (anna, organizer):
        [latest, *_] = items(client, user)
        assert latest["type"] == "participant_removed"
        assert latest["participant"]["id"] == anna["id"]


def test_remove_not_joined_does_not_notify(
    client: TestClient, organizer: User, event: dict[str, Any], anna: User, db: Session
) -> None:
    response = remove(client, organizer, event["id"], anna["id"])

    assert response.json()["detail"]["code"] == "participant_not_found"
    assert db.scalar(select(func.count()).select_from(Notification)) == 0


# --- запись и отказ ---


def test_join_notifies_organizer(
    client: TestClient, organizer: User, event: dict[str, Any], oleg: User
) -> None:
    assert join(client, oleg, event["id"]).status_code == 200

    [notification] = items(client, organizer)
    assert notification["type"] == "participant_joined"
    assert notification["participant"] == {"id": oleg["id"], "name": "Олег"}
    assert notification["changed_fields"] is None
    assert notification["read"] is False
    assert items(client, oleg) == []


def test_join_and_leave_create_two_notifications(
    client: TestClient, organizer: User, event: dict[str, Any], oleg: User, clock: FakeClock
) -> None:
    assert join(client, oleg, event["id"]).status_code == 200
    clock.advance(1)
    assert (
        client.post(f"/api/events/{event['id']}/leave", headers=auth_header(oleg)).status_code
        == 200
    )

    assert types(client, organizer) == ["participant_left", "participant_joined"]


def test_full_event_join_does_not_notify(
    client: TestClient, organizer: User, anna: User, oleg: User
) -> None:
    event = create_event(client, organizer, max_participants=2)
    assert join(client, anna, event["id"]).status_code == 200

    response = join(client, oleg, event["id"])

    assert response.json()["detail"]["code"] == "event_full"
    assert len(items(client, organizer)) == 1


def test_concurrent_join_for_last_place_creates_one_notification(
    client: TestClient, organizer: User, anna: User, oleg: User
) -> None:
    event = create_event(client, organizer, max_participants=2)

    results = run_together(
        lambda: join(client, anna, event["id"]), lambda: join(client, oleg, event["id"])
    )

    assert sorted(r.status_code for r in results) == [200, 409]
    [notification] = items(client, organizer)
    winner = anna if results[0].status_code == 200 else oleg
    assert notification["participant"]["id"] == winner["id"]


def test_notifications_are_atomic_with_action(
    app: FastAPI,
    organizer: User,
    event: dict[str, Any],
    oleg: User,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = notification_service.notify_participant_joined

    def failing(session: Session, *args: Any) -> None:
        original(session, *args)
        session.flush()
        raise RuntimeError("сбой базы данных")

    monkeypatch.setattr(notification_service, "notify_participant_joined", failing)
    client = TestClient(app, raise_server_exceptions=False)

    assert join(client, oleg, event["id"]).status_code == 500

    assert db.scalar(select(func.count()).select_from(Notification)) == 0
    assert (
        db.scalar(
            select(func.count())
            .select_from(EventParticipant)
            .where(EventParticipant.user_id == uuid.UUID(oleg["id"]))
        )
        == 0
    )


# --- напоминание об окне отзывов ---


def remind(db: Session, now: datetime) -> int:
    return notification_service.create_review_reminders(db, now)


def test_reminder_when_window_opens(
    client: TestClient,
    db: Session,
    organizer: User,
    anna: User,
    oleg: User,
    joined: dict[str, Any],
) -> None:
    assert remind(db, REVIEWS_OPEN - timedelta(minutes=1)) == 0
    assert remind(db, REVIEWS_OPEN) == 3

    for user in (organizer, anna, oleg):
        reminders = [i for i in items(client, user) if i["type"] == "review_reminder"]
        assert len(reminders) == 1
        assert reminders[0]["event"] == {"id": joined["id"], "title": "Мафия"}


def test_reminder_repeated_run_creates_no_duplicates(
    db: Session, organizer: User, joined: dict[str, Any]
) -> None:
    assert remind(db, REVIEWS_OPEN) == 3
    assert remind(db, REVIEWS_OPEN + timedelta(hours=1)) == 0


def test_reminder_concurrent_runs_create_one_each(
    app: FastAPI, db: Session, organizer: User, joined: dict[str, Any]
) -> None:
    def run() -> int:
        with app.state.session_factory() as session:
            return notification_service.create_review_reminders(session, REVIEWS_OPEN)

    results = run_together(run, run)

    assert sum(results) == 3
    count = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.type == NotificationType.REVIEW_REMINDER)
    )
    assert count == 3


def test_reminder_not_created_for_single_participant(
    db: Session, organizer: User, event: dict[str, Any]
) -> None:
    assert remind(db, REVIEWS_OPEN) == 0


def test_reminder_not_created_after_window_closed(
    db: Session, organizer: User, joined: dict[str, Any]
) -> None:
    assert remind(db, REVIEWS_CLOSE) == 0
    assert remind(db, REVIEWS_CLOSE - timedelta(minutes=1)) == 3


# --- список, число непрочитанных, отметка ---


def add_notifications(db: Session, user: User, count: int, *, read: int = 0) -> None:
    """Добавляет `count` уведомлений с разным временем; первые `read` — прочитаны."""
    for index in range(count):
        created = START + timedelta(minutes=index)
        db.add(
            Notification(
                user_id=uuid.UUID(user["id"]),
                type=NotificationType.EVENT_DELETED,
                event_title=f"Мероприятие {index}",
                created_at=created,
                read_at=created if index < read else None,
            )
        )
    db.commit()


def test_list_returns_latest_20_and_unread_count(
    client: TestClient, db: Session, anna: User
) -> None:
    add_notifications(db, anna, 25, read=3)

    body = notifications(client, anna)

    assert len(body["items"]) == 20
    assert body["items"][0]["event"]["title"] == "Мероприятие 24"
    assert body["items"][-1]["event"]["title"] == "Мероприятие 5"
    assert body["unread_count"] == 22


def test_list_with_exactly_20(client: TestClient, db: Session, anna: User) -> None:
    add_notifications(db, anna, 20)

    assert len(items(client, anna)) == 20


def test_empty_list(client: TestClient, anna: User) -> None:
    assert notifications(client, anna) == {"items": [], "unread_count": 0}


def test_admin_sees_only_own_notifications(client: TestClient, db: Session, anna: User) -> None:
    admin = register(client, ADMIN_PHONE, name="Админ")
    add_notifications(db, anna, 2)

    assert notifications(client, admin) == {"items": [], "unread_count": 0}


def test_unread_count_after_join(
    client: TestClient, organizer: User, event: dict[str, Any], oleg: User
) -> None:
    url = "/api/notifications/unread-count"
    assert client.get(url, headers=auth_header(organizer)).json() == {"unread_count": 0}

    assert join(client, oleg, event["id"]).status_code == 200

    assert client.get(url, headers=auth_header(organizer)).json() == {"unread_count": 1}


def test_participant_name_is_current(
    client: TestClient, organizer: User, event: dict[str, Any], oleg: User
) -> None:
    assert join(client, oleg, event["id"]).status_code == 200
    response = client.patch("/api/profile", json={"name": "Олег П."}, headers=auth_header(oleg))
    assert response.status_code == 200

    assert items(client, organizer)[0]["participant"]["name"] == "Олег П."


def test_title_is_snapshot(
    client: TestClient, organizer: User, event: dict[str, Any], oleg: User
) -> None:
    assert join(client, oleg, event["id"]).status_code == 200
    assert patch_event(client, organizer, event["id"], title="Новое название").status_code == 200

    assert items(client, organizer)[0]["event"]["title"] == "Мафия"


def test_mark_read_up_to_newest(client: TestClient, db: Session, anna: User) -> None:
    add_notifications(db, anna, 3)
    newest = items(client, anna)[0]["created_at"]

    assert mark_read(client, anna, newest).status_code == 204

    body = notifications(client, anna)
    assert body["unread_count"] == 0
    assert all(item["read"] for item in body["items"])


def test_mark_read_keeps_later_notifications(
    client: TestClient,
    organizer: User,
    event: dict[str, Any],
    anna: User,
    oleg: User,
    clock: FakeClock,
) -> None:
    assert join(client, anna, event["id"]).status_code == 200
    shown = items(client, organizer)[0]["created_at"]
    clock.advance(5)
    assert join(client, oleg, event["id"]).status_code == 200

    assert mark_read(client, organizer, shown).status_code == 204

    body = notifications(client, organizer)
    assert body["unread_count"] == 1
    assert [(i["participant"]["name"], i["read"]) for i in body["items"]] == [
        ("Олег", False),
        ("Анна", True),
    ]


def test_mark_read_twice(client: TestClient, db: Session, anna: User) -> None:
    add_notifications(db, anna, 2)
    newest = items(client, anna)[0]["created_at"]

    assert mark_read(client, anna, newest).status_code == 204
    first = db.scalars(select(Notification.read_at).order_by(Notification.created_at)).all()
    assert mark_read(client, anna, newest).status_code == 204
    db.expire_all()

    assert db.scalars(select(Notification.read_at).order_by(Notification.created_at)).all() == first


@pytest.mark.parametrize(
    "body",
    [{}, {"up_to": "2026-10-31T12:00:00"}, {"up_to": "2026-10-31T12:00:00Z", "all": True}],
)
def test_mark_read_validation(client: TestClient, anna: User, body: dict[str, Any]) -> None:
    response = client.post("/api/notifications/read", json=body, headers=auth_header(anna))

    assert response.status_code == 422


# --- доступ ---


@pytest.mark.parametrize(
    "request_",
    [
        lambda c: c.get("/api/notifications"),
        lambda c: c.get("/api/notifications/unread-count"),
        lambda c: c.post("/api/notifications/read", json={"up_to": "2026-10-31T12:00:00Z"}),
    ],
)
def test_notifications_require_token(
    client: TestClient, request_: Callable[[TestClient], Any]
) -> None:
    assert request_(client).status_code == 401


def test_draft_can_read_notifications(client: TestClient) -> None:
    draft = login(client, DRAFT)

    assert client.get("/api/notifications", headers=auth_header(draft)).status_code == 200
    response = client.get("/api/notifications/unread-count", headers=auth_header(draft))
    assert response.json() == {"unread_count": 0}
