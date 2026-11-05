import uuid
from datetime import date, datetime

from sqlalchemy import delete, exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.errors import AppError, forbidden, not_found
from app.models import Category, City, Event, EventParticipant, User, UserInterest
from app.models.user import EMAIL_UNIQUE_INDEX, PHONE_UNIQUE_CONSTRAINT
from app.schemas.city import CityOut
from app.schemas.profile import (
    AdminProfileUpdate,
    InterestOut,
    ProfileOut,
    ProfileStats,
    ProfileUpdate,
)
from app.services.auth_service import lock_phone, revoke_pending_codes, revoke_user_refresh_tokens

MIN_BIRTH_DATE = date(1900, 1, 1)


def get_profile_for(session: Session, viewer: User, user_id: uuid.UUID) -> User:
    """Чужой профиль: себе, админу и тем, кто записан с владельцем на одно мероприятие
    (в том числе прошедшее; организатор тоже записан). Остальным 403 — и для
    несуществующего id, чтобы не раскрывать существование пользователя."""
    if user_id == viewer.id:
        return viewer
    if viewer.is_admin:
        user = session.get(User, user_id)
        if user is None:
            raise not_found("Пользователь не найден")
        return user

    mine = aliased(EventParticipant)
    theirs = aliased(EventParticipant)
    shared_event = exists().where(
        mine.event_id == theirs.event_id,
        mine.user_id == viewer.id,
        theirs.user_id == User.id,
    )
    user = session.scalar(select(User).where(User.id == user_id, shared_event))
    if user is None:
        raise forbidden()
    return user


def build_profile(session: Session, user: User, now: datetime) -> ProfileOut:
    """Профиль с городом, интересами и счётчиками мероприятий."""
    city = session.get(City, user.city_id) if user.city_id is not None else None
    interests = session.execute(
        select(Category.id, Category.name, Category.icon)
        .join(UserInterest, UserInterest.category_id == Category.id)
        .where(UserInterest.user_id == user.id)
        .order_by(Category.id)
    ).all()
    organized = session.scalar(
        select(func.count()).select_from(Event).where(Event.organizer_id == user.id)
    )
    attended = session.scalar(
        select(func.count())
        .select_from(EventParticipant)
        .join(Event, Event.id == EventParticipant.event_id)
        .where(
            EventParticipant.user_id == user.id,
            Event.organizer_id != user.id,
            Event.starts_at <= now,
        )
    )
    return ProfileOut.from_user(
        user,
        now.date(),
        city=CityOut.model_validate(city) if city else None,
        interests=[InterestOut(id=i, name=name, icon=icon) for i, name, icon in interests],
        stats=ProfileStats(organized_count=organized or 0, attended_count=attended or 0),
    )


def update_own_profile(session: Session, now: datetime, user: User, data: ProfileUpdate) -> User:
    _apply_common_fields(session, user, data, now.date())
    _save(session)
    return user


def update_profile_by_admin(
    session: Session, now: datetime, user_id: uuid.UUID, data: AdminProfileUpdate
) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise not_found("Пользователь не найден")

    old_phone = user.phone
    phone_changed = data.phone is not None and data.phone != old_phone
    if phone_changed:
        # Те же блокировки, что и при входе, чтобы не пересечься с запросом/проверкой кода.
        # Берём их до изменений, иначе autoflush запроса блокировки обойдёт обработку 409
        for phone in sorted((old_phone, str(data.phone))):
            lock_phone(session, phone)

    _apply_common_fields(session, user, data, now.date())
    if phone_changed:
        user.phone = str(data.phone)
    # Явный flush: конфликты уникальности дают 409 до отзыва сессий
    _save(session, commit=False)

    if phone_changed:
        revoke_user_refresh_tokens(session, user.id, now)
        revoke_pending_codes(session, old_phone, now)
    _save(session)
    return user


def _apply_common_fields(session: Session, user: User, data: ProfileUpdate, today: date) -> None:
    fields = data.model_fields_set
    if "birth_date" in fields and data.birth_date is not None:
        _validate_birth_date(data.birth_date, today)
    if "city_id" in fields and data.city_id is not None and session.get(City, data.city_id) is None:
        raise AppError(422, "city_not_found", "Город не найден")
    if "interest_ids" in fields and data.interest_ids:
        known = session.scalar(
            select(func.count()).select_from(Category).where(Category.id.in_(data.interest_ids))
        )
        if known != len(data.interest_ids):
            raise AppError(422, "category_not_found", "Категория не найдена")

    if "name" in fields:
        user.name = data.name
    if "birth_date" in fields:
        user.birth_date = data.birth_date
    if "email" in fields:
        user.email = str(data.email) if data.email is not None else None
    if "telegram" in fields:
        user.telegram = data.telegram
    if "about" in fields:
        user.about = data.about
    if "city_id" in fields:
        user.city_id = data.city_id
    if "interest_ids" in fields and data.interest_ids is not None:
        # Набор интересов заменяется целиком в той же транзакции
        session.execute(delete(UserInterest).where(UserInterest.user_id == user.id))
        session.add_all(
            UserInterest(user_id=user.id, category_id=category_id)
            for category_id in data.interest_ids
        )


def _validate_birth_date(birth_date: date, today: date) -> None:
    if birth_date > today or birth_date < MIN_BIRTH_DATE:
        raise AppError(
            422,
            "invalid_birth_date",
            f"Дата рождения должна быть между {MIN_BIRTH_DATE.isoformat()} и текущей датой",
        )


def _save(session: Session, *, commit: bool = True) -> None:
    """Сохраняет изменения профиля, превращая нарушение уникальности в 409."""
    try:
        if commit:
            session.commit()
        else:
            session.flush()
    except IntegrityError as exc:
        session.rollback()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint == EMAIL_UNIQUE_INDEX:
            raise AppError(409, "email_taken", "Этот email уже используется") from exc
        if constraint == PHONE_UNIQUE_CONSTRAINT:
            raise AppError(409, "phone_taken", "Этот телефон уже используется") from exc
        raise
