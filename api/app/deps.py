import uuid
from collections.abc import Callable, Iterator
from datetime import datetime
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import AppError, forbidden, unauthorized
from app.models import Role, User
from app.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


def get_now(request: Request) -> datetime:
    now: datetime = request.app.state.clock()
    return now


SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[Session, Depends(get_session)]
NowDep = Annotated[datetime, Depends(get_now)]


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: SessionDep,
    settings: SettingsDep,
    now: NowDep,
) -> User:
    if credentials is None:
        raise unauthorized()
    try:
        payload = decode_access_token(credentials.credentials, now, settings)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise unauthorized("Недействительный или просроченный токен") from exc
    user = session.get(User, user_id)
    if user is None:
        raise unauthorized("Пользователь не найден")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def completed_user(user: CurrentUser) -> User:
    if not user.profile_completed:
        raise AppError(403, "profile_incomplete", "Заполните имя и дату рождения в профиле")
    return user


CompletedUser = Annotated[User, Depends(completed_user)]


def admin_user(user: CompletedUser) -> User:
    if not user.is_admin:
        raise forbidden()
    return user


AdminUser = Annotated[User, Depends(admin_user)]


def require_role(role: Role) -> Callable[[User], User]:
    """Зависимость: заполненный профиль и роль role, иначе 403."""

    def dependency(user: CompletedUser) -> User:
        if role not in user.roles:
            raise forbidden()
        return user

    return dependency


OrganizerUser = Annotated[User, Depends(require_role(Role.ORGANIZER))]
ParticipantUser = Annotated[User, Depends(require_role(Role.PARTICIPANT))]
