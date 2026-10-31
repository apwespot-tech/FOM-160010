import hmac
import math
import uuid
from datetime import datetime, timedelta

from sqlalchemy import ColumnElement, and_, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import AppError, unauthorized
from app.models import AuthCode, RefreshToken, Role, User, UserRole
from app.schemas.auth import TokenPair
from app.security import create_access_token, generate_code, generate_refresh_token, hash_token

DEFAULT_ROLES = (Role.PARTICIPANT, Role.ORGANIZER)


def lock_phone(session: Session, phone: str) -> None:
    """Сериализует операции входа по одному номеру до конца транзакции."""
    session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:phone))"), {"phone": phone})


def _active_code_filter(phone: str, now: datetime, settings: Settings) -> ColumnElement[bool]:
    return and_(
        AuthCode.phone == phone,
        AuthCode.used_at.is_(None),
        AuthCode.revoked_at.is_(None),
        AuthCode.expires_at > now,
        AuthCode.attempts < settings.auth_code_max_attempts,
    )


def revoke_pending_codes(session: Session, phone: str, now: datetime) -> None:
    session.execute(
        update(AuthCode)
        .where(AuthCode.phone == phone, AuthCode.used_at.is_(None), AuthCode.revoked_at.is_(None))
        .values(revoked_at=now)
    )


def revoke_user_refresh_tokens(session: Session, user_id: uuid.UUID, now: datetime) -> None:
    session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )


def request_code(session: Session, settings: Settings, now: datetime, phone: str) -> int:
    """Создаёт новый код для номера и возвращает срок его действия в секундах."""
    lock_phone(session, phone)

    last_created_at = session.scalar(
        select(AuthCode.created_at)
        .where(AuthCode.phone == phone)
        .order_by(AuthCode.created_at.desc())
        .limit(1)
    )
    if last_created_at is not None:
        elapsed = (now - last_created_at).total_seconds()
        if elapsed < settings.auth_code_cooldown_seconds:
            retry_after = math.ceil(settings.auth_code_cooldown_seconds - elapsed)
            session.rollback()
            raise AppError(
                429,
                "code_cooldown",
                "Код можно запросить повторно позже",
                headers={"Retry-After": str(retry_after)},
                extra={"retry_after": retry_after},
            )

    revoke_pending_codes(session, phone, now)
    session.add(
        AuthCode(
            phone=phone,
            code=generate_code(),
            created_at=now,
            expires_at=now + timedelta(seconds=settings.auth_code_ttl_seconds),
        )
    )
    session.commit()
    return settings.auth_code_ttl_seconds


def get_active_code(session: Session, settings: Settings, now: datetime, phone: str) -> str | None:
    return session.scalar(
        select(AuthCode.code)
        .where(_active_code_filter(phone, now, settings))
        .order_by(AuthCode.created_at.desc())
        .limit(1)
    )


def verify_code(
    session: Session, settings: Settings, now: datetime, phone: str, code: str
) -> TokenPair:
    lock_phone(session, phone)

    auth_code = session.scalar(
        select(AuthCode)
        .where(_active_code_filter(phone, now, settings))
        .order_by(AuthCode.created_at.desc())
        .limit(1)
    )
    if auth_code is None:
        session.rollback()
        raise AppError(400, "invalid_code", "Неверный или просроченный код")
    if not hmac.compare_digest(auth_code.code, code):
        auth_code.attempts += 1
        session.commit()
        raise AppError(400, "invalid_code", "Неверный или просроченный код")

    auth_code.used_at = now
    user = _get_or_create_user(session, phone)
    tokens = _issue_tokens(session, settings, now, user)
    session.commit()
    return tokens


def refresh_tokens(
    session: Session, settings: Settings, now: datetime, refresh_token: str
) -> TokenPair:
    # Атомарная ротация: из одновременных запросов строку получит только один
    user_id = session.scalar(
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == hash_token(refresh_token),
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        .values(revoked_at=now)
        .returning(RefreshToken.user_id)
    )
    user = session.get(User, user_id) if user_id is not None else None
    if user is None:
        session.rollback()
        raise unauthorized("Недействительный refresh-токен")

    tokens = _issue_tokens(session, settings, now, user)
    session.commit()
    return tokens


def logout(session: Session, now: datetime, refresh_token: str) -> None:
    session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == hash_token(refresh_token),
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    session.commit()


def _get_or_create_user(session: Session, phone: str) -> User:
    created_id = session.scalar(
        insert(User)
        .values(id=uuid.uuid4(), phone=phone)
        .on_conflict_do_nothing(index_elements=[User.phone])
        .returning(User.id)
    )
    user = session.scalars(select(User).where(User.phone == phone)).one()
    if created_id is not None:
        user.role_rows.extend(UserRole(role=role) for role in DEFAULT_ROLES)
    return user


def _sync_admin_role(settings: Settings, user: User) -> None:
    should_be_admin = user.phone in settings.admin_phone_set
    if should_be_admin and not user.is_admin:
        user.role_rows.append(UserRole(role=Role.ADMIN))
    elif not should_be_admin and user.is_admin:
        user.role_rows = [row for row in user.role_rows if row.role != Role.ADMIN]


def _issue_tokens(session: Session, settings: Settings, now: datetime, user: User) -> TokenPair:
    _sync_admin_role(settings, user)
    refresh_token = generate_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            created_at=now,
            expires_at=now + timedelta(seconds=settings.refresh_token_ttl_seconds),
        )
    )
    return TokenPair(
        access_token=create_access_token(user.id, sorted(user.roles), now, settings),
        refresh_token=refresh_token,
        expires_in=settings.access_token_ttl_seconds,
        refresh_expires_in=settings.refresh_token_ttl_seconds,
    )
