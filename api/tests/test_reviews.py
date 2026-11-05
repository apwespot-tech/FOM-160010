"""Отзывы: право оставить, окно, создание, валидация, уникальность, анонимность,
изменение и удаление, списки и доступ."""

from datetime import datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Event, Review
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

ORGANIZER = "+79991230001"
ALICE = "+79991230002"
BOB = "+79991230003"
STRANGER = "+79991230004"
MISSING_ID = "00000000-0000-0000-0000-000000000000"
# Мероприятие начинается через сутки после START
STARTS_AT = START + timedelta(days=1)
OPENS_AT = STARTS_AT + timedelta(hours=24)
CLOSES_AT = STARTS_AT + timedelta(days=8)


def error_code(response: Any) -> str:
    code: str = response.json()["detail"]["code"]
    return code


def set_now(
    client: TestClient, clock: FakeClock, people: dict[str, dict[str, Any]], moment: datetime
) -> None:
    """Переводит часы и заново входит всеми: access-токен живёт 15 минут."""
    clock.current = moment
    for person in people.values():
        person.update(login(client, person["phone"]))


def post_review(
    client: TestClient, user: dict[str, Any], event_id: str, target: dict[str, Any], **body: Any
) -> Any:
    payload = {"target_id": target["id"], "stars": 5, **body}
    return client.post(f"/api/events/{event_id}/reviews", json=payload, headers=auth_header(user))


def patch_review(client: TestClient, user: dict[str, Any], review_id: str, **body: Any) -> Any:
    return client.patch(f"/api/reviews/{review_id}", json=body, headers=auth_header(user))


def delete_review(client: TestClient, user: dict[str, Any], review_id: str) -> Any:
    return client.delete(f"/api/reviews/{review_id}", headers=auth_header(user))


def mine(client: TestClient, user: dict[str, Any], event_id: str) -> Any:
    return client.get(f"/api/events/{event_id}/reviews/mine", headers=auth_header(user))


def about(client: TestClient, user: dict[str, Any], target_id: str, **params: Any) -> Any:
    return client.get(f"/api/users/{target_id}/reviews", params=params, headers=auth_header(user))


@pytest.fixture
def people(client: TestClient) -> dict[str, dict[str, Any]]:
    phones = {"organizer": ORGANIZER, "alice": ALICE, "bob": BOB, "stranger": STRANGER}
    names = {"organizer": "Олег", "alice": "Алиса", "bob": "Борис", "stranger": "Сергей"}
    return {
        key: {**register(client, phone, name=names[key]), "phone": phone}
        for key, phone in phones.items()
    }


@pytest.fixture
def event(client: TestClient, people: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Мероприятие с организатором, Алисой и Борисом; Сергей не записан."""
    created = create_event(client, people["organizer"], starts_at=STARTS_AT.isoformat())
    for name in ("alice", "bob"):
        assert join(client, people[name], created["id"]).status_code == 200
    return created


@pytest.fixture
def in_window(
    client: TestClient, clock: FakeClock, people: dict[str, dict[str, Any]], event: dict[str, Any]
) -> dict[str, Any]:
    set_now(client, clock, people, OPENS_AT + timedelta(hours=1))
    return event


# --- право оставить отзыв ---


def test_participant_reviews_organizer(client: TestClient, people: Any, in_window: Any) -> None:
    response = post_review(client, people["alice"], in_window["id"], people["organizer"])
    assert response.status_code == 201, response.text
    assert response.json()["kind"] == "organizer"


def test_participant_reviews_participant(client: TestClient, people: Any, in_window: Any) -> None:
    response = post_review(client, people["alice"], in_window["id"], people["bob"])
    assert response.status_code == 201
    assert response.json()["kind"] == "participant"


def test_organizer_reviews_participant(client: TestClient, people: Any, in_window: Any) -> None:
    response = post_review(client, people["organizer"], in_window["id"], people["alice"])
    assert response.status_code == 201
    assert response.json()["kind"] == "participant"


def test_review_about_self(client: TestClient, people: Any, in_window: Any) -> None:
    response = post_review(client, people["alice"], in_window["id"], people["alice"])
    assert response.status_code == 422
    assert error_code(response) == "review_target_invalid"


def test_target_not_on_event(client: TestClient, people: Any, in_window: Any) -> None:
    response = post_review(client, people["alice"], in_window["id"], people["stranger"])
    assert response.status_code == 422
    assert error_code(response) == "review_target_invalid"


def test_author_not_on_event(client: TestClient, people: Any, in_window: Any) -> None:
    response = post_review(client, people["stranger"], in_window["id"], people["organizer"])
    assert response.status_code == 403
    assert error_code(response) == "not_participant"


def test_admin_not_on_event(client: TestClient, people: Any, in_window: Any) -> None:
    admin = register(client, ADMIN_PHONE, name="Админ")
    response = post_review(client, admin, in_window["id"], people["organizer"])
    assert response.status_code == 403
    assert error_code(response) == "not_participant"


# --- окно отзывов ---


def test_window_not_open_yet(client: TestClient, clock: FakeClock, people: Any, event: Any) -> None:
    set_now(client, clock, people, OPENS_AT - timedelta(minutes=1))
    response = post_review(client, people["alice"], event["id"], people["organizer"])
    assert response.status_code == 409
    assert error_code(response) == "review_not_open"


def test_window_first_moment(client: TestClient, clock: FakeClock, people: Any, event: Any) -> None:
    set_now(client, clock, people, OPENS_AT)
    response = post_review(client, people["alice"], event["id"], people["organizer"])
    assert response.status_code == 201


def test_window_last_moment_update(
    client: TestClient, clock: FakeClock, people: Any, in_window: Any
) -> None:
    created = post_review(client, people["alice"], in_window["id"], people["organizer"]).json()
    set_now(client, clock, people, CLOSES_AT - timedelta(minutes=1))
    response = patch_review(client, people["alice"], created["id"], stars=3)
    assert response.status_code == 200
    assert response.json()["stars"] == 3


def test_window_closed(client: TestClient, clock: FakeClock, people: Any, in_window: Any) -> None:
    created = post_review(client, people["alice"], in_window["id"], people["organizer"]).json()
    set_now(client, clock, people, CLOSES_AT)

    create = post_review(client, people["alice"], in_window["id"], people["bob"])
    update = patch_review(client, people["alice"], created["id"], stars=1)
    remove = delete_review(client, people["alice"], created["id"])

    for response in (create, update, remove):
        assert response.status_code == 409
        assert error_code(response) == "review_closed"
    assert (
        about(client, people["alice"], people["organizer"]["id"], kind="organizer").json()["items"][
            0
        ]["stars"]
        == 5
    )


def test_upcoming_event(client: TestClient, people: Any, event: Any) -> None:
    response = post_review(client, people["alice"], event["id"], people["organizer"])
    assert response.status_code == 409
    assert error_code(response) == "review_not_open"


# --- создание и валидация ---


def test_create_review_response(client: TestClient, people: Any, in_window: Any) -> None:
    response = post_review(
        client, people["alice"], in_window["id"], people["organizer"], text="Отлично организовано"
    )
    assert response.status_code == 201
    body = response.json()
    assert body["stars"] == 5
    assert body["text"] == "Отлично организовано"
    assert body["anonymous"] is False
    assert body["target_id"] == people["organizer"]["id"]
    assert body["event"] == {"id": in_window["id"], "title": in_window["title"]}
    assert body["author"] == {"id": people["alice"]["id"], "name": "Алиса", "avatar_id": None}
    assert body["created_at"] == body["updated_at"]


def test_review_without_text(client: TestClient, people: Any, in_window: Any) -> None:
    response = post_review(client, people["alice"], in_window["id"], people["organizer"], stars=4)
    assert response.status_code == 201
    assert (response.json()["text"], response.json()["anonymous"]) == (None, False)


def test_review_missing_event(client: TestClient, people: Any, in_window: Any) -> None:
    response = post_review(client, people["alice"], MISSING_ID, people["organizer"])
    assert response.status_code == 404


@pytest.mark.parametrize("stars", [0, 6, 4.5, "5", True])
def test_stars_invalid(client: TestClient, people: Any, in_window: Any, stars: Any) -> None:
    response = post_review(
        client, people["alice"], in_window["id"], people["organizer"], stars=stars
    )
    assert response.status_code == 422


@pytest.mark.parametrize("stars", [1, 5])
def test_stars_bounds(client: TestClient, people: Any, in_window: Any, stars: int) -> None:
    response = post_review(
        client, people["alice"], in_window["id"], people["organizer"], stars=stars
    )
    assert response.status_code == 201


def test_text_length(client: TestClient, people: Any, in_window: Any) -> None:
    ok = post_review(
        client, people["alice"], in_window["id"], people["organizer"], text=" " + "а" * 1000 + " "
    )
    too_long = post_review(client, people["alice"], in_window["id"], people["bob"], text="а" * 1001)
    assert ok.status_code == 201
    assert len(ok.json()["text"]) == 1000
    assert too_long.status_code == 422


def test_blank_text_is_null(client: TestClient, people: Any, in_window: Any) -> None:
    response = post_review(
        client, people["alice"], in_window["id"], people["organizer"], text="   "
    )
    assert response.status_code == 201
    assert response.json()["text"] is None


def test_unknown_field(client: TestClient, people: Any, in_window: Any) -> None:
    response = post_review(client, people["alice"], in_window["id"], people["organizer"], kind="x")
    assert response.status_code == 422


# --- один отзыв на пару ---


def test_duplicate_review(client: TestClient, people: Any, in_window: Any) -> None:
    first = post_review(client, people["alice"], in_window["id"], people["organizer"], stars=4)
    second = post_review(client, people["alice"], in_window["id"], people["organizer"], stars=1)
    assert first.status_code == 201
    assert second.status_code == 409
    assert error_code(second) == "review_exists"
    items = mine(client, people["alice"], in_window["id"]).json()["items"]
    assert [item["stars"] for item in items] == [4]


def test_concurrent_duplicates(
    client: TestClient, db: Session, people: Any, in_window: Any
) -> None:
    results = run_together(
        lambda: post_review(client, people["alice"], in_window["id"], people["organizer"]),
        lambda: post_review(client, people["alice"], in_window["id"], people["organizer"]),
    )
    assert sorted(response.status_code for response in results) == [201, 409]
    assert error_code(next(r for r in results if r.status_code == 409)) == "review_exists"
    assert db.scalar(select(func.count()).select_from(Review)) == 1


def test_different_events(client: TestClient, clock: FakeClock, people: Any, event: Any) -> None:
    second = create_event(
        client, people["organizer"], starts_at=(STARTS_AT + timedelta(hours=1)).isoformat()
    )
    assert join(client, people["alice"], second["id"]).status_code == 200
    set_now(client, clock, people, OPENS_AT + timedelta(hours=2))

    for event_id in (event["id"], second["id"]):
        assert (
            post_review(client, people["alice"], event_id, people["organizer"]).status_code == 201
        )


def test_review_again_after_delete(client: TestClient, people: Any, in_window: Any) -> None:
    created = post_review(client, people["alice"], in_window["id"], people["organizer"]).json()
    assert delete_review(client, people["alice"], created["id"]).status_code == 204
    again = post_review(client, people["alice"], in_window["id"], people["organizer"])
    assert again.status_code == 201


# --- анонимность ---


@pytest.fixture
def anonymous_review(client: TestClient, people: Any, in_window: Any) -> dict[str, Any]:
    response = post_review(
        client, people["alice"], in_window["id"], people["organizer"], anonymous=True
    )
    assert response.status_code == 201
    review: dict[str, Any] = response.json()
    return review


def test_author_sees_own_anonymous_review(
    client: TestClient, people: Any, in_window: Any, anonymous_review: Any
) -> None:
    assert anonymous_review["author"]["id"] == people["alice"]["id"]
    assert anonymous_review["anonymous"] is True
    own = mine(client, people["alice"], in_window["id"]).json()["items"][0]
    assert own["author"]["id"] == people["alice"]["id"]
    listed = about(client, people["alice"], people["organizer"]["id"], kind="organizer").json()
    assert listed["items"][0]["author"]["id"] == people["alice"]["id"]
    updated = patch_review(client, people["alice"], anonymous_review["id"], stars=4).json()
    assert updated["author"]["id"] == people["alice"]["id"]


@pytest.mark.parametrize("viewer", ["organizer", "bob"])
def test_anonymous_hidden_from_others(
    client: TestClient, people: Any, anonymous_review: Any, viewer: str
) -> None:
    listed = about(client, people[viewer], people["organizer"]["id"], kind="organizer").json()
    assert listed["items"][0]["author"] is None
    assert listed["items"][0]["anonymous"] is True


def test_anonymous_visible_to_admin(client: TestClient, people: Any, anonymous_review: Any) -> None:
    admin = register(client, ADMIN_PHONE, name="Админ")
    listed = about(client, admin, people["organizer"]["id"], kind="organizer").json()
    assert listed["items"][0]["author"]["id"] == people["alice"]["id"]
    assert listed["items"][0]["anonymous"] is True


def test_open_review_author_without_contacts(
    client: TestClient, people: Any, in_window: Any
) -> None:
    post_review(client, people["alice"], in_window["id"], people["organizer"])
    author = about(client, people["bob"], people["organizer"]["id"], kind="organizer").json()[
        "items"
    ][0]["author"]
    assert set(author) == {"id", "name", "avatar_id"}


# --- изменение ---


def test_update_review(client: TestClient, clock: FakeClock, people: Any, in_window: Any) -> None:
    created = post_review(client, people["alice"], in_window["id"], people["bob"], stars=3).json()
    clock.advance(60)
    response = patch_review(client, people["alice"], created["id"], stars=5, text="  ")
    assert response.status_code == 200
    body = response.json()
    assert (body["stars"], body["text"]) == (5, None)
    assert body["created_at"] == created["created_at"]
    assert body["updated_at"] != created["updated_at"]


def test_remove_anonymity(client: TestClient, people: Any, anonymous_review: Any) -> None:
    response = patch_review(client, people["alice"], anonymous_review["id"], anonymous=False)
    assert response.status_code == 200
    listed = about(client, people["bob"], people["organizer"]["id"], kind="organizer").json()
    assert listed["items"][0]["author"]["id"] == people["alice"]["id"]


@pytest.mark.parametrize("editor", ["organizer", "admin"])
def test_update_foreign_review(
    client: TestClient, people: Any, in_window: Any, editor: str
) -> None:
    created = post_review(client, people["alice"], in_window["id"], people["organizer"]).json()
    user = register(client, ADMIN_PHONE, name="Админ") if editor == "admin" else people[editor]
    response = patch_review(client, user, created["id"], stars=1)
    assert response.status_code == 403
    assert mine(client, people["alice"], in_window["id"]).json()["items"][0]["stars"] == 5


@pytest.mark.parametrize(
    "body", [{"target_id": MISSING_ID}, {"stars": None}, {"anonymous": None}, {"stars": 0}]
)
def test_update_invalid(
    client: TestClient, people: Any, in_window: Any, body: dict[str, Any]
) -> None:
    created = post_review(client, people["alice"], in_window["id"], people["organizer"]).json()
    assert patch_review(client, people["alice"], created["id"], **body).status_code == 422


def test_update_missing(client: TestClient, people: Any, in_window: Any) -> None:
    assert patch_review(client, people["alice"], MISSING_ID, stars=3).status_code == 404


# --- удаление ---


def test_author_deletes_in_window(client: TestClient, people: Any, in_window: Any) -> None:
    created = post_review(client, people["alice"], in_window["id"], people["organizer"]).json()
    assert delete_review(client, people["alice"], created["id"]).status_code == 204
    assert mine(client, people["alice"], in_window["id"]).json()["items"] == []


def test_target_cannot_delete(client: TestClient, people: Any, in_window: Any) -> None:
    created = post_review(client, people["alice"], in_window["id"], people["organizer"]).json()
    assert delete_review(client, people["organizer"], created["id"]).status_code == 403
    assert len(mine(client, people["alice"], in_window["id"]).json()["items"]) == 1


def test_delete_missing(client: TestClient, people: Any, in_window: Any) -> None:
    assert delete_review(client, people["alice"], MISSING_ID).status_code == 404


def test_admin_deletes_after_window(
    client: TestClient, clock: FakeClock, people: Any, in_window: Any
) -> None:
    created = post_review(client, people["alice"], in_window["id"], people["organizer"]).json()
    set_now(client, clock, people, STARTS_AT + timedelta(days=30))
    admin = register(client, ADMIN_PHONE, name="Админ")
    assert delete_review(client, admin, created["id"]).status_code == 204
    listed = about(client, admin, people["organizer"]["id"], kind="organizer").json()
    assert listed == {"items": [], "total": 0}


def test_concurrent_delete(client: TestClient, people: Any, in_window: Any) -> None:
    created = post_review(client, people["alice"], in_window["id"], people["organizer"]).json()
    admin = register(client, ADMIN_PHONE, name="Админ")
    results = run_together(
        lambda: delete_review(client, admin, created["id"]),
        lambda: delete_review(client, people["alice"], created["id"]),
    )
    assert sorted(response.status_code for response in results) == [204, 404]


def test_author_window_closed_after_event_deleted(
    client: TestClient, db: Session, people: Any, in_window: Any
) -> None:
    created = post_review(client, people["alice"], in_window["id"], people["organizer"]).json()
    db.execute(delete(Event).where(Event.id == in_window["id"]))
    db.commit()
    response = patch_review(client, people["alice"], created["id"], stars=1)
    assert response.status_code == 409
    assert error_code(response) == "review_closed"


# --- свои отзывы по мероприятию ---


def test_my_reviews(client: TestClient, clock: FakeClock, people: Any, in_window: Any) -> None:
    post_review(client, people["alice"], in_window["id"], people["organizer"])
    clock.advance(60)
    post_review(client, people["alice"], in_window["id"], people["bob"], stars=3)
    post_review(client, people["bob"], in_window["id"], people["organizer"])

    response = mine(client, people["alice"], in_window["id"])
    assert response.status_code == 200
    body = response.json()
    assert [item["target_id"] for item in body["items"]] == [
        people["organizer"]["id"],
        people["bob"]["id"],
    ]
    assert datetime.fromisoformat(body["opens_at"]) == OPENS_AT
    assert datetime.fromisoformat(body["closes_at"]) == CLOSES_AT


def test_my_reviews_empty(client: TestClient, people: Any, event: Any) -> None:
    body = mine(client, people["bob"], event["id"]).json()
    assert body["items"] == []
    assert datetime.fromisoformat(body["opens_at"]) == OPENS_AT


def test_my_reviews_stranger(client: TestClient, people: Any, event: Any) -> None:
    assert mine(client, people["stranger"], event["id"]).status_code == 403
    assert mine(client, people["stranger"], MISSING_ID).status_code == 403


def test_my_reviews_admin_missing(client: TestClient) -> None:
    admin = register(client, ADMIN_PHONE, name="Админ")
    assert mine(client, admin, MISSING_ID).status_code == 404


# --- отзывы о пользователе ---


def test_reviews_about_user_by_kind(
    client: TestClient, clock: FakeClock, people: Any, in_window: Any
) -> None:
    post_review(client, people["alice"], in_window["id"], people["organizer"], stars=4)
    clock.advance(60)
    post_review(client, people["bob"], in_window["id"], people["organizer"], stars=5)
    post_review(client, people["alice"], in_window["id"], people["bob"], stars=3)

    response = about(client, people["alice"], people["organizer"]["id"], kind="organizer")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [item["stars"] for item in body["items"]] == [5, 4]
    assert {item["kind"] for item in body["items"]} == {"organizer"}

    participant = about(client, people["alice"], people["organizer"]["id"], kind="participant")
    assert participant.json() == {"items": [], "total": 0}


def test_reviews_about_user_pagination(
    client: TestClient, clock: FakeClock, people: Any, in_window: Any
) -> None:
    for name in ("alice", "bob"):
        post_review(client, people[name], in_window["id"], people["organizer"])
        clock.advance(60)
    page = about(
        client, people["alice"], people["organizer"]["id"], kind="organizer", limit=1, offset=1
    ).json()
    assert page["total"] == 2
    assert page["items"][0]["author"]["id"] == people["alice"]["id"]


def test_reviews_about_user_own(client: TestClient, people: Any, anonymous_review: Any) -> None:
    listed = about(client, people["organizer"], people["organizer"]["id"], kind="organizer").json()
    assert listed["total"] == 1
    assert listed["items"][0]["author"] is None


def test_reviews_about_user_without_access(client: TestClient, people: Any, event: Any) -> None:
    response = about(client, people["stranger"], people["organizer"]["id"], kind="organizer")
    assert response.status_code == 403
    assert about(client, people["stranger"], MISSING_ID, kind="organizer").status_code == 403


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"kind": "other"},
        {"kind": "organizer", "limit": 0},
        {"kind": "organizer", "limit": 101},
        {"kind": "organizer", "offset": -1},
    ],
)
def test_reviews_about_user_invalid_params(
    client: TestClient, people: Any, event: Any, params: dict[str, Any]
) -> None:
    response = about(client, people["alice"], people["organizer"]["id"], **params)
    assert response.status_code == 422


def test_reviews_after_event_deleted(
    client: TestClient, db: Session, people: Any, in_window: Any
) -> None:
    post_review(client, people["alice"], in_window["id"], people["organizer"])
    db.execute(delete(Event).where(Event.id == in_window["id"]))
    db.commit()
    admin = register(client, ADMIN_PHONE, name="Админ")
    item = about(client, admin, people["organizer"]["id"], kind="organizer").json()["items"][0]
    assert item["event"] == {"id": None, "title": in_window["title"]}


# --- доступ ---


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", f"/api/events/{MISSING_ID}/reviews"),
        ("GET", f"/api/events/{MISSING_ID}/reviews/mine"),
        ("PATCH", f"/api/reviews/{MISSING_ID}"),
        ("DELETE", f"/api/reviews/{MISSING_ID}"),
        ("GET", f"/api/users/{MISSING_ID}/reviews"),
    ],
)
def test_reviews_require_token(client: TestClient, method: str, path: str) -> None:
    assert client.request(method, path).status_code == 401


def test_draft_cannot_read_reviews(client: TestClient, people: Any) -> None:
    draft = login(client, "+79991230099")
    response = about(client, draft, people["organizer"]["id"], kind="organizer")
    assert response.status_code == 403
    assert error_code(response) == "profile_incomplete"
