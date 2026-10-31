import uuid
from datetime import date, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError, forbidden, not_found
from app.models import User
from app.models.user import EMAIL_UNIQUE_INDEX, PHONE_UNIQUE_CONSTRAINT
from app.schemas.profile import AdminProfileUpdate, ProfileUpdate
from app.services.auth_service import lock_phone, revoke_pending_codes, revoke_user_refresh_tokens

MIN_BIRTH_DATE = date(1900, 1, 1)


def get_profile_for(session: Session, viewer: User, user_id: uuid.UUID) -> User:
    """Чужой профиль: себе и админу; остальным 403 без раскрытия существования."""
    if user_id == viewer.id:
        return viewer
    if not viewer.is_admin:
        raise forbidden()
    user = session.get(User, user_id)
    if user is None:
        raise not_found("Пользователь не найден")
    return user


def update_own_profile(session: Session, now: datetime, user: User, data: ProfileUpdate) -> User:
    _apply_common_fields(user, data, now.date())
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

    _apply_common_fields(user, data, now.date())
    if phone_changed:
        user.phone = str(data.phone)
    # Явный flush: конфликты уникальности дают 409 до отзыва сессий
    _save(session, commit=False)

    if phone_changed:
        revoke_user_refresh_tokens(session, user.id, now)
        revoke_pending_codes(session, old_phone, now)
    _save(session)
    return user


def _apply_common_fields(user: User, data: ProfileUpdate, today: date) -> None:
    fields = data.model_fields_set
    if "birth_date" in fields and data.birth_date is not None:
        _validate_birth_date(data.birth_date, today)

    if "name" in fields:
        user.name = data.name
    if "birth_date" in fields:
        user.birth_date = data.birth_date
    if "email" in fields:
        user.email = str(data.email) if data.email is not None else None
    if "telegram" in fields:
        user.telegram = data.telegram
    if "photo_url" in fields:
        user.photo_url = str(data.photo_url) if data.photo_url is not None else None


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
