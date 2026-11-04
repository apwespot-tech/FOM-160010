import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Category,
    CategoryCover,
    Event,
    EventParticipant,
    EventPhoto,
    EventPhotoData,
    RefreshToken,
    Role,
    User,
    UserRole,
)

NOW = datetime(2026, 10, 31, tzinfo=UTC)


def test_phone_is_unique(db: Session) -> None:
    db.add(User(phone="+79991110001"))
    db.commit()
    db.add(User(phone="+79991110001"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_email_is_unique_case_insensitive(db: Session) -> None:
    db.add(User(phone="+79991110001", email="ann@example.com"))
    db.commit()
    db.add(User(phone="+79991110002", email="Ann@Example.com"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_many_users_without_email(db: Session) -> None:
    db.add_all([User(phone="+79991110001"), User(phone="+79991110002")])
    db.commit()


def test_user_delete_cascades_roles_and_tokens(db: Session) -> None:
    user = User(phone="+79991110001", role_rows=[UserRole(role=Role.PARTICIPANT)])
    db.add(user)
    db.flush()
    db.add(
        RefreshToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash="a" * 64,
            created_at=NOW,
            expires_at=NOW,
        )
    )
    db.commit()

    # Удаляем на уровне SQL, чтобы проверить ON DELETE CASCADE, а не каскад ORM
    db.execute(delete(User).where(User.id == user.id))
    db.commit()

    assert db.scalar(select(func.count()).select_from(UserRole)) == 0
    assert db.scalar(select(func.count()).select_from(RefreshToken)) == 0


# --- мероприятия ---


def _event(organizer_id: uuid.UUID, **overrides: object) -> Event:
    fields: dict[str, object] = {
        "organizer_id": organizer_id,
        "category_id": 1,
        "title": "t",
        "description": "d",
        "place": "p",
        "starts_at": NOW,
        "max_participants": 5,
        "min_age": 0,
    }
    fields.update(overrides)
    return Event(**fields)


@pytest.mark.parametrize(
    "overrides",
    [
        {"max_participants": 1},
        {"max_participants": 101},
        {"min_age": 12},
        {"duration_minutes": 0},
        {"duration_minutes": 1441},
    ],
)
def test_event_check_constraints(db: Session, overrides: dict[str, object]) -> None:
    user = User(phone="+79991110001")
    db.add(user)
    db.flush()
    db.add(_event(user.id, **overrides))
    with pytest.raises(IntegrityError):
        db.commit()


def test_participant_is_unique_per_event(db: Session) -> None:
    user = User(phone="+79991110001")
    db.add(user)
    db.flush()
    event = _event(user.id)
    db.add(event)
    db.flush()
    db.add(EventParticipant(event_id=event.id, user_id=user.id, joined_at=NOW))
    db.commit()
    db.add(EventParticipant(event_id=event.id, user_id=user.id, joined_at=NOW))
    with pytest.raises(IntegrityError):
        db.commit()


def test_event_delete_cascades_participants(db: Session) -> None:
    user = User(phone="+79991110001")
    db.add(user)
    db.flush()
    event = _event(user.id)
    db.add(event)
    db.flush()
    db.add(EventParticipant(event_id=event.id, user_id=user.id, joined_at=NOW))
    db.commit()

    db.execute(delete(Event).where(Event.id == event.id))
    db.commit()

    assert db.scalar(select(func.count()).select_from(EventParticipant)) == 0


# --- фото мероприятий ---


def _event_with_owner(db: Session) -> Event:
    user = User(phone="+79991110001")
    db.add(user)
    db.flush()
    event = _event(user.id)
    db.add(event)
    db.flush()
    return event


def _photo(event_id: uuid.UUID, **overrides: object) -> EventPhoto:
    fields: dict[str, object] = {
        "event_id": event_id,
        "position": 0,
        "content_type": "image/jpeg",
        "size_bytes": 3,
        "created_at": NOW,
    }
    fields.update(overrides)
    return EventPhoto(**fields)


@pytest.mark.parametrize(
    "overrides", [{"position": 10}, {"position": -1}, {"content_type": "image/gif"}]
)
def test_event_photo_check_constraints(db: Session, overrides: dict[str, object]) -> None:
    event = _event_with_owner(db)
    db.add(_photo(event.id, **overrides))
    with pytest.raises(IntegrityError):
        db.commit()


def test_event_photo_position_is_unique_per_event(db: Session) -> None:
    event = _event_with_owner(db)
    db.add_all([_photo(event.id, position=3), _photo(event.id, position=3)])
    with pytest.raises(IntegrityError):
        db.commit()


def test_event_delete_cascades_photos(db: Session) -> None:
    event = _event_with_owner(db)
    photo = _photo(event.id)
    db.add(photo)
    db.flush()
    db.add(EventPhotoData(photo_id=photo.id, data=b"abc", thumb=b"t"))
    db.commit()

    db.execute(delete(Event).where(Event.id == event.id))
    db.commit()

    assert db.scalar(select(func.count()).select_from(EventPhoto)) == 0
    assert db.scalar(select(func.count()).select_from(EventPhotoData)) == 0


# --- категории ---


def _cover(db: Session) -> CategoryCover:
    cover = CategoryCover(content_type="image/webp", data=b"full", thumb=b"thumb")
    db.add(cover)
    db.flush()
    return cover


def test_category_requires_cover(db: Session) -> None:
    db.add(Category(name="Квесты", icon="pi-key"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_category_requires_icon(db: Session) -> None:
    cover = _cover(db)
    db.add(Category(name="Квесты", cover_id=cover.id))
    with pytest.raises(IntegrityError):
        db.commit()


@pytest.mark.parametrize("icon", ["🎲", "video", "pi-Video", "pi video", ""])
def test_category_icon_format(db: Session, icon: str) -> None:
    cover = _cover(db)
    db.add(Category(name="Квесты", icon=icon, cover_id=cover.id))
    with pytest.raises(IntegrityError):
        db.commit()


def test_category_cover_cannot_be_deleted_while_used(db: Session) -> None:
    cover_id = db.scalar(select(Category.cover_id).where(Category.name == "Кино"))

    with pytest.raises(IntegrityError):
        db.execute(delete(CategoryCover).where(CategoryCover.id == cover_id))
        db.commit()
