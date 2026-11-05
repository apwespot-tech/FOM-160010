"""Рейтинги: расчёт, профиль, организатор в мероприятии и строки участников."""

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Event, Review, ReviewKind, User
from tests.conftest import auth_header, create_event, join, register

ORGANIZER = "+79991240001"
MEMBER = "+79991240002"
PAST = datetime(2026, 10, 1, tzinfo=UTC)


def add_reviews(db: Session, target_id: str, kind: ReviewKind, stars: list[int]) -> None:
    """Отзывы напрямую в БД: каждый — от нового автора по отдельному прошедшему мероприятию."""
    for value in stars:
        count = db.query(User).count()
        author = User(phone=f"+7999126{count:04d}")
        db.add(author)
        db.flush()
        event = Event(
            organizer_id=target_id if kind == ReviewKind.ORGANIZER else author.id,
            category_id=1,
            city_id=1,
            title="Прошедшее",
            description="d",
            place="p",
            starts_at=PAST,
            max_participants=10,
            min_age=0,
        )
        db.add(event)
        db.flush()
        db.add(
            Review(
                event_id=event.id,
                event_title=event.title,
                author_id=author.id,
                target_id=target_id,
                kind=kind,
                stars=value,
                created_at=PAST,
                updated_at=PAST,
            )
        )
    db.commit()


def profile(client: TestClient, user: dict[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = client.get("/api/profile", headers=auth_header(user)).json()
    return body


@pytest.fixture
def organizer(client: TestClient) -> dict[str, Any]:
    return register(client, ORGANIZER, name="Олег")


@pytest.fixture
def member(client: TestClient) -> dict[str, Any]:
    return register(client, MEMBER, name="Мария")


# --- профиль и расчёт ---


def test_new_profile_ratings(client: TestClient, organizer: dict[str, Any]) -> None:
    assert profile(client, organizer)["ratings"] == {
        "as_organizer": {"average": None, "count": 0},
        "as_participant": {"average": None, "count": 0},
    }


@pytest.mark.parametrize(
    ("stars", "expected"),
    [([5, 5, 4], 4.7), ([5, 5, 5, 4], 4.8), ([4, 4, 5], 4.3), ([5, 5, 5], 5.0), ([1, 2], None)],
)
def test_average(
    client: TestClient,
    db: Session,
    organizer: dict[str, Any],
    stars: list[int],
    expected: float | None,
) -> None:
    add_reviews(db, organizer["id"], ReviewKind.ORGANIZER, stars)
    assert profile(client, organizer)["ratings"]["as_organizer"] == {
        "average": expected,
        "count": len(stars),
    }


def test_kinds_are_separate(client: TestClient, db: Session, organizer: dict[str, Any]) -> None:
    add_reviews(db, organizer["id"], ReviewKind.ORGANIZER, [5, 5, 4])
    add_reviews(db, organizer["id"], ReviewKind.PARTICIPANT, [3, 3])
    assert profile(client, organizer)["ratings"] == {
        "as_organizer": {"average": 4.7, "count": 3},
        "as_participant": {"average": None, "count": 2},
    }


def test_delete_review_lowers_count(
    client: TestClient, db: Session, organizer: dict[str, Any]
) -> None:
    add_reviews(db, organizer["id"], ReviewKind.PARTICIPANT, [5, 4, 4])
    assert profile(client, organizer)["ratings"]["as_participant"]["average"] == 4.3

    review = db.scalars(select(Review)).first()
    assert review is not None
    db.delete(review)
    db.commit()

    assert profile(client, organizer)["ratings"]["as_participant"] == {
        "average": None,
        "count": 2,
    }


def test_foreign_profile_ratings(
    client: TestClient, db: Session, organizer: dict[str, Any], member: dict[str, Any]
) -> None:
    event = create_event(client, organizer)
    assert join(client, member, event["id"]).status_code == 200
    add_reviews(db, organizer["id"], ReviewKind.ORGANIZER, [5, 5, 4])

    response = client.get(f"/api/profile/{organizer['id']}", headers=auth_header(member))
    assert response.status_code == 200
    assert response.json()["ratings"] == profile(client, organizer)["ratings"]


# --- мероприятие ---


def test_organizer_rating_in_event(
    client: TestClient, db: Session, organizer: dict[str, Any], member: dict[str, Any]
) -> None:
    event = create_event(client, organizer)
    add_reviews(db, organizer["id"], ReviewKind.ORGANIZER, [5, 5, 4])

    single = client.get(f"/api/events/{event['id']}", headers=auth_header(member)).json()
    catalog = client.get("/api/events", headers=auth_header(member)).json()["items"]
    assert single["organizer"]["rating"] == 4.7
    assert catalog[0]["organizer"]["rating"] == 4.7


def test_organizer_with_few_reviews(
    client: TestClient, db: Session, organizer: dict[str, Any]
) -> None:
    event = create_event(client, organizer)
    add_reviews(db, organizer["id"], ReviewKind.ORGANIZER, [5, 5])
    add_reviews(db, organizer["id"], ReviewKind.PARTICIPANT, [5, 5, 5, 5, 5])

    body = client.get(f"/api/events/{event['id']}", headers=auth_header(organizer)).json()
    assert body["organizer"]["rating"] is None


def test_ratings_in_participants(
    client: TestClient, db: Session, organizer: dict[str, Any], member: dict[str, Any]
) -> None:
    event = create_event(client, organizer)
    assert join(client, member, event["id"]).status_code == 200
    add_reviews(db, organizer["id"], ReviewKind.ORGANIZER, [5, 5, 4])
    add_reviews(db, organizer["id"], ReviewKind.PARTICIPANT, [4, 4, 4])
    add_reviews(db, member["id"], ReviewKind.PARTICIPANT, [5, 4, 5, 4])
    add_reviews(db, member["id"], ReviewKind.ORGANIZER, [1, 1, 1])

    rows = client.get(f"/api/events/{event['id']}/participants", headers=auth_header(member)).json()
    assert [(row["id"], row["rating"]) for row in rows] == [
        (organizer["id"], 4.7),
        (member["id"], 4.5),
    ]


def test_participant_without_rating(
    client: TestClient, db: Session, organizer: dict[str, Any], member: dict[str, Any]
) -> None:
    event = create_event(client, organizer)
    assert join(client, member, event["id"]).status_code == 200
    add_reviews(db, member["id"], ReviewKind.PARTICIPANT, [5, 5])

    rows = client.get(
        f"/api/events/{event['id']}/participants", headers=auth_header(organizer)
    ).json()
    assert rows[1]["rating"] is None
    assert set(rows[1]) == {"id", "name", "avatar_id", "telegram", "rating"}
