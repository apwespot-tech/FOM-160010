import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Category,
    CategoryCover,
    City,
    Event,
    EventParticipant,
    EventPhoto,
    EventPhotoData,
    RefreshToken,
    Review,
    ReviewKind,
    Role,
    User,
    UserImage,
    UserInterest,
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
        "city_id": 1,
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


# --- города, картинки и интересы пользователей ---


@pytest.mark.parametrize("name", ["Москва", "москва", "МОСКВА"])
def test_city_name_is_unique_case_insensitive(db: Session, name: str) -> None:
    db.add(City(name=name))
    with pytest.raises(IntegrityError):
        db.commit()


@pytest.mark.parametrize("name", ["Кино", "кино"])
def test_category_name_is_unique_case_insensitive(db: Session, name: str) -> None:
    cover = _cover(db)
    db.add(Category(name=name, icon="pi-video", cover_id=cover.id))
    with pytest.raises(IntegrityError):
        db.commit()


def test_event_requires_city(db: Session) -> None:
    user = User(phone="+79991110001")
    db.add(user)
    db.flush()
    db.add(_event(user.id, city_id=None))
    with pytest.raises(IntegrityError):
        db.commit()


def test_city_with_events_cannot_be_deleted(db: Session) -> None:
    _event_with_owner(db)
    db.commit()

    with pytest.raises(IntegrityError):
        db.execute(delete(City).where(City.id == 1))
        db.commit()


def test_user_delete_cascades_images_and_interests(db: Session) -> None:
    user = User(phone="+79991110001")
    db.add(user)
    db.flush()
    image = UserImage(
        user_id=user.id, content_type="image/webp", data=b"d", thumb=b"t", created_at=NOW
    )
    db.add(image)
    db.add(UserInterest(user_id=user.id, category_id=1))
    db.flush()
    user.avatar_id = image.id
    db.commit()

    db.execute(delete(User).where(User.id == user.id))
    db.commit()

    assert db.scalar(select(func.count()).select_from(UserImage)) == 0
    assert db.scalar(select(func.count()).select_from(UserInterest)) == 0


# --- отзывы ---


def _review_setup(db: Session) -> tuple[Event, User, User]:
    author, target = User(phone="+79991110011"), User(phone="+79991110012")
    db.add_all([author, target])
    db.flush()
    event = _event(target.id)
    db.add(event)
    db.flush()
    return event, author, target


def _review(event: Event, author: User, target: User, **overrides: object) -> Review:
    fields: dict[str, object] = {
        "event_id": event.id,
        "event_title": event.title,
        "author_id": author.id,
        "target_id": target.id,
        "kind": ReviewKind.ORGANIZER,
        "stars": 5,
        "created_at": NOW,
        "updated_at": NOW,
    }
    fields.update(overrides)
    return Review(**fields)


@pytest.mark.parametrize("stars", [1, 5])
def test_review_stars_bounds_accepted(db: Session, stars: int) -> None:
    event, author, target = _review_setup(db)
    db.add(_review(event, author, target, stars=stars))
    db.commit()


@pytest.mark.parametrize("stars", [0, 6])
def test_review_stars_out_of_range(db: Session, stars: int) -> None:
    event, author, target = _review_setup(db)
    db.add(_review(event, author, target, stars=stars))
    with pytest.raises(IntegrityError):
        db.commit()


def test_review_about_self_rejected(db: Session) -> None:
    event, author, _ = _review_setup(db)
    db.add(_review(event, author, author))
    with pytest.raises(IntegrityError):
        db.commit()


def test_review_unique_per_event_author_target(db: Session) -> None:
    event, author, target = _review_setup(db)
    db.add(_review(event, author, target))
    db.commit()
    db.add(_review(event, author, target, stars=3))
    with pytest.raises(IntegrityError):
        db.commit()


def test_review_survives_event_delete(db: Session) -> None:
    event, author, target = _review_setup(db)
    review = _review(event, author, target, event_title="Настолки")
    db.add(review)
    db.commit()

    db.execute(delete(Event).where(Event.id == event.id))
    db.commit()
    db.expire_all()

    row = db.execute(select(Review.event_id, Review.event_title)).one()
    assert row == (None, "Настолки")
