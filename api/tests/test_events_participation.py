"""Участие: запись, возраст, лимит, отказ, удаление участника, список, доступ."""

import threading
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import EventParticipant, Role
from tests.conftest import (
    ADMIN_PHONE,
    START,
    FakeClock,
    auth_header,
    create_event,
    join,
    login,
    register,
    set_roles,
    upload_avatar,
)

ORGANIZER = "+79991234567"
OTHER = "+79991234568"
THIRD = "+79991234569"
MISSING_ID = "00000000-0000-0000-0000-000000000000"
SOON = (START + timedelta(minutes=10)).isoformat()


def leave(client: TestClient, user: dict[str, Any], event_id: str) -> Any:
    return client.post(f"/api/events/{event_id}/leave", headers=auth_header(user))


def remove(client: TestClient, user: dict[str, Any], event_id: str, user_id: str) -> Any:
    return client.post(
        f"/api/events/{event_id}/participants/{user_id}/remove", headers=auth_header(user)
    )


def participants(client: TestClient, user: dict[str, Any], event_id: str) -> Any:
    return client.get(f"/api/events/{event_id}/participants", headers=auth_header(user))


def error_code(response: Any) -> str:
    code: str = response.json()["detail"]["code"]
    return code


def count_participants(db: Session, event_id: str) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(EventParticipant)
            .where(EventParticipant.event_id == event_id)
        )
        or 0
    )


# --- запись ---


def test_join(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    other = register(client, OTHER)
    event = create_event(client, organizer)

    response = join(client, other, event["id"])

    assert response.status_code == 200
    assert response.json()["is_joined"] is True
    assert response.json()["participants_count"] == 2


def test_join_twice(client: TestClient, db: Session) -> None:
    organizer = register(client, ORGANIZER)
    other = register(client, OTHER)
    event = create_event(client, organizer)
    join(client, other, event["id"])

    response = join(client, other, event["id"])

    assert response.status_code == 409
    assert error_code(response) == "already_joined"
    assert count_participants(db, event["id"]) == 2


def test_organizer_joins_own_event(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    event = create_event(client, organizer)

    response = join(client, organizer, event["id"])

    assert response.status_code == 409
    assert error_code(response) == "already_joined"


def test_join_requires_participant_role(client: TestClient, db: Session) -> None:
    organizer = register(client, ORGANIZER)
    other = register(client, OTHER)
    set_roles(db, other["id"], [Role.ORGANIZER])
    event = create_event(client, organizer)

    response = join(client, other, event["id"])

    assert response.status_code == 403
    assert error_code(response) == "forbidden"


def test_join_missing_event(client: TestClient) -> None:
    user = register(client, OTHER)
    assert join(client, user, MISSING_ID).status_code == 404


# --- возраст (START = 2026-10-31) ---


def test_younger_than_min_age(client: TestClient, db: Session) -> None:
    organizer = register(client, ORGANIZER)
    teen = register(client, OTHER, birth_date="2009-03-01")  # 17 лет
    event = create_event(client, organizer, min_age=18)

    response = join(client, teen, event["id"])

    assert response.status_code == 403
    assert error_code(response) == "age_restricted"
    assert count_participants(db, event["id"]) == 1


def test_min_age_reached_today(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    user = register(client, OTHER, birth_date="2008-10-31")  # 18 сегодня
    event = create_event(client, organizer, min_age=18)

    assert join(client, user, event["id"]).status_code == 200


def test_age_is_checked_on_today_not_on_event_date(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    user = register(client, OTHER, birth_date="2008-11-01")  # 18 исполнится завтра
    in_three_days = (START + timedelta(days=3)).isoformat()
    event = create_event(client, organizer, min_age=18, starts_at=in_three_days)

    response = join(client, user, event["id"])

    assert response.status_code == 403
    assert error_code(response) == "age_restricted"


def test_no_age_restriction(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    child = register(client, OTHER, birth_date="2020-01-01")
    event = create_event(client, organizer, min_age=0)

    assert join(client, child, event["id"]).status_code == 200


# --- лимит мест ---


def test_join_last_place_and_full(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    second = register(client, OTHER)
    third = register(client, THIRD)
    fourth = register(client, "+79991234570")
    event = create_event(client, organizer, max_participants=3)
    join(client, second, event["id"])

    last = join(client, third, event["id"])
    full = join(client, fourth, event["id"])

    assert last.status_code == 200
    assert last.json()["is_full"] is True
    assert full.status_code == 409
    assert error_code(full) == "event_full"


def test_place_is_freed_after_leave(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    second = register(client, OTHER)
    third = register(client, THIRD)
    event = create_event(client, organizer, max_participants=2)
    join(client, second, event["id"])
    assert join(client, third, event["id"]).status_code == 409

    assert leave(client, second, event["id"]).status_code == 200
    assert join(client, third, event["id"]).status_code == 200


# --- после начала ---


def test_join_and_leave_after_start(client: TestClient, clock: FakeClock, db: Session) -> None:
    organizer = register(client, ORGANIZER)
    second = register(client, OTHER)
    third = register(client, THIRD)
    event = create_event(client, organizer, starts_at=SOON)
    join(client, second, event["id"])
    clock.advance(10 * 60)  # ровно starts_at

    joined = join(client, third, event["id"])
    left = leave(client, second, event["id"])
    removed = remove(client, organizer, event["id"], second["id"])

    for response in (joined, left, removed):
        assert response.status_code == 409
        assert error_code(response) == "event_started"
    assert count_participants(db, event["id"]) == 2


def test_join_one_second_before_start(client: TestClient, clock: FakeClock) -> None:
    organizer = register(client, ORGANIZER)
    other = register(client, OTHER)
    event = create_event(client, organizer, starts_at=SOON)
    clock.advance(10 * 60 - 1)

    assert join(client, other, event["id"]).status_code == 200


# --- отказ ---


def test_leave(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    other = register(client, OTHER)
    event = create_event(client, organizer)
    join(client, other, event["id"])

    response = leave(client, other, event["id"])

    assert response.status_code == 200
    assert response.json()["is_joined"] is False
    assert response.json()["participants_count"] == 1
    assert join(client, other, event["id"]).status_code == 200


def test_leave_without_joining(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    other = register(client, OTHER)
    event = create_event(client, organizer)

    response = leave(client, other, event["id"])

    assert response.status_code == 409
    assert error_code(response) == "not_joined"


def test_organizer_cannot_leave(client: TestClient, db: Session) -> None:
    organizer = register(client, ORGANIZER)
    event = create_event(client, organizer)

    response = leave(client, organizer, event["id"])

    assert response.status_code == 409
    assert error_code(response) == "organizer_cannot_leave"
    assert count_participants(db, event["id"]) == 1


def test_leave_missing_event(client: TestClient) -> None:
    user = register(client, OTHER)
    assert leave(client, user, MISSING_ID).status_code == 404


# --- удаление участника ---


def test_organizer_removes_participant(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    other = register(client, OTHER)
    event = create_event(client, organizer)
    join(client, other, event["id"])

    response = remove(client, organizer, event["id"], other["id"])

    assert response.status_code == 200
    assert response.json()["free_places"] == 4
    ids = [item["id"] for item in participants(client, organizer, event["id"]).json()]
    assert other["id"] not in ids
    assert join(client, other, event["id"]).status_code == 200


def test_admin_removes_participant(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    other = register(client, OTHER)
    admin = register(client, ADMIN_PHONE)
    event = create_event(client, organizer)
    join(client, other, event["id"])

    assert remove(client, admin, event["id"], other["id"]).status_code == 200


def test_participant_cannot_remove_another(client: TestClient, db: Session) -> None:
    organizer = register(client, ORGANIZER)
    second = register(client, OTHER)
    third = register(client, THIRD)
    event = create_event(client, organizer)
    join(client, second, event["id"])
    join(client, third, event["id"])

    response = remove(client, second, event["id"], third["id"])

    assert response.status_code == 403
    assert count_participants(db, event["id"]) == 3


def test_remove_not_joined_user(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    other = register(client, OTHER)
    event = create_event(client, organizer)

    response = remove(client, organizer, event["id"], other["id"])

    assert response.status_code == 404
    assert error_code(response) == "participant_not_found"


def test_cannot_remove_organizer(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    admin = register(client, ADMIN_PHONE)
    event = create_event(client, organizer)

    response = remove(client, admin, event["id"], organizer["id"])

    assert response.status_code == 409
    assert error_code(response) == "organizer_cannot_leave"


def test_remove_from_missing_event(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    assert remove(client, organizer, MISSING_ID, organizer["id"]).status_code == 404


# --- список участников ---


def test_participants_list(client: TestClient) -> None:
    organizer = register(client, ORGANIZER, name="Анна", email="anna@example.com")
    other = register(
        client,
        OTHER,
        name="Борис",
        telegram="@boris_k",
    )
    boris_avatar = upload_avatar(client, other)
    event = create_event(client, organizer)
    join(client, other, event["id"])

    response = participants(client, other, event["id"])

    assert response.status_code == 200
    assert response.json() == [
        {"id": organizer["id"], "name": "Анна", "avatar_id": None, "telegram": None},
        {
            "id": other["id"],
            "name": "Борис",
            "avatar_id": boris_avatar,
            "telegram": "@boris_k",
        },
    ]


def test_participants_forbidden_for_outsider(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    outsider = register(client, OTHER)
    event = create_event(client, organizer)

    assert participants(client, outsider, event["id"]).status_code == 403
    assert participants(client, outsider, MISSING_ID).status_code == 403


def test_participants_for_admin(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    admin = register(client, ADMIN_PHONE)
    event = create_event(client, organizer)

    assert participants(client, admin, event["id"]).status_code == 200
    assert participants(client, admin, MISSING_ID).status_code == 404


def test_former_participant_loses_access(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    other = register(client, OTHER)
    event = create_event(client, organizer)
    join(client, other, event["id"])
    leave(client, other, event["id"])

    assert participants(client, other, event["id"]).status_code == 403


def test_participants_after_start(client: TestClient, clock: FakeClock) -> None:
    organizer = register(client, ORGANIZER)
    event = create_event(client, organizer, starts_at=SOON)
    clock.advance(11 * 60)

    assert participants(client, organizer, event["id"]).status_code == 200


# --- конкурентность ---


def run_concurrently(*actions: Any) -> list[Any]:
    barrier = threading.Barrier(len(actions))
    results: list[Any] = [None] * len(actions)

    def worker(index: int) -> None:
        barrier.wait()
        results[index] = actions[index]()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(len(actions))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results


def test_concurrent_join_for_last_place(client: TestClient, db: Session) -> None:
    organizer = register(client, ORGANIZER)
    users = [register(client, f"+7999555{index:04d}") for index in range(5)]
    event = create_event(client, organizer, max_participants=2)

    results = run_concurrently(*(lambda u=u: join(client, u, event["id"]) for u in users))

    statuses = sorted(response.status_code for response in results)
    assert statuses == [200, 409, 409, 409, 409]
    assert all(error_code(r) == "event_full" for r in results if r.status_code == 409)
    assert count_participants(db, event["id"]) == 2


def test_concurrent_leave(client: TestClient, db: Session) -> None:
    organizer = register(client, ORGANIZER)
    other = register(client, OTHER)
    event = create_event(client, organizer)
    join(client, other, event["id"])

    results = run_concurrently(
        lambda: leave(client, other, event["id"]), lambda: leave(client, other, event["id"])
    )

    assert sorted(r.status_code for r in results) == [200, 409]
    assert error_code(next(r for r in results if r.status_code == 409)) == "not_joined"
    assert count_participants(db, event["id"]) == 1


def test_concurrent_limit_decrease_and_join(client: TestClient, db: Session) -> None:
    organizer = register(client, ORGANIZER)
    joined = [register(client, f"+7999666{index:04d}") for index in range(2)]
    newcomer = register(client, OTHER)
    event = create_event(client, organizer, max_participants=5)
    for user in joined:
        join(client, user, event["id"])

    patch, join_result = run_concurrently(
        lambda: client.patch(
            f"/api/events/{event['id']}",
            json={"max_participants": 3},
            headers=auth_header(organizer),
        ),
        lambda: join(client, newcomer, event["id"]),
    )

    if patch.status_code == 200:
        assert join_result.status_code == 409
        assert error_code(join_result) == "event_full"
        assert count_participants(db, event["id"]) == 3
    else:
        assert patch.status_code == 409
        assert error_code(patch) == "limit_below_participants"
        assert join_result.status_code == 200
        assert count_participants(db, event["id"]) == 4


# --- доступ ---


ENDPOINTS = [
    ("GET", "/api/events"),
    ("POST", "/api/events"),
    ("GET", "/api/events/{id}"),
    ("PATCH", "/api/events/{id}"),
    ("DELETE", "/api/events/{id}"),
    ("POST", "/api/events/{id}/join"),
    ("POST", "/api/events/{id}/leave"),
    ("GET", "/api/events/{id}/participants"),
    ("POST", "/api/events/{id}/participants/{id}/remove"),
]


@pytest.mark.parametrize(("method", "path"), ENDPOINTS)
def test_requires_token(client: TestClient, method: str, path: str) -> None:
    response = client.request(method, path.format(id=MISSING_ID), json={})
    assert response.status_code == 401


@pytest.mark.parametrize(("method", "path"), ENDPOINTS)
def test_requires_completed_profile(client: TestClient, method: str, path: str) -> None:
    draft = login(client, OTHER)
    response = client.request(
        method, path.format(id=MISSING_ID), json={}, headers=auth_header(draft)
    )
    assert response.status_code == 403
    assert error_code(response) == "profile_incomplete"
