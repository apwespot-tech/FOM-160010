"""Аватар и обложка профиля: загрузка, удаление, отдача."""

import enum
import uuid
from datetime import datetime
from typing import BinaryIO

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import User, UserImage
from app.services.photo_processing import process_photo, read_limited
from app.services.photo_service import THUMB_CONTENT_TYPE, PhotoSize


class ProfileImageKind(enum.StrEnum):
    AVATAR = "avatar"
    COVER = "cover"


def _column(kind: ProfileImageKind) -> str:
    return "avatar_id" if kind is ProfileImageKind.AVATAR else "cover_id"


def _lock_user(session: Session, user_id: uuid.UUID) -> User:
    """Строка пользователя под FOR UPDATE со свежими значениями: замены картинок идут по очереди."""
    user = session.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert user is not None
    return user


def set_image(
    session: Session, now: datetime, user: User, kind: ProfileImageKind, stream: BinaryIO
) -> None:
    """Сохраняет новую картинку, переставляет ссылку и удаляет прежнюю — в одной транзакции."""
    # Проверка и пересохранение файла — до блокировки строки пользователя
    photo = process_photo(read_limited(stream, 0), 0)

    locked = _lock_user(session, user.id)
    previous: uuid.UUID | None = getattr(locked, _column(kind))
    image = UserImage(
        id=uuid.uuid4(),
        user_id=locked.id,
        content_type=photo.content_type,
        data=photo.data,
        thumb=photo.thumb,
        created_at=now,
    )
    session.add(image)
    # Картинка вставляется раньше ссылки на неё (users <-> user_images ссылаются друг на друга)
    session.flush()
    setattr(locked, _column(kind), image.id)
    session.flush()
    if previous is not None:
        session.execute(delete(UserImage).where(UserImage.id == previous))
    session.commit()


def delete_image(session: Session, user: User, kind: ProfileImageKind) -> None:
    locked = _lock_user(session, user.id)
    previous: uuid.UUID | None = getattr(locked, _column(kind))
    setattr(locked, _column(kind), None)
    session.flush()
    if previous is not None:
        session.execute(delete(UserImage).where(UserImage.id == previous))
    session.commit()


def get_image(
    session: Session, user_id: uuid.UUID, image_id: uuid.UUID, size: PhotoSize
) -> tuple[bytes, str]:
    """Текущий аватар или обложка пользователя; чужая или заменённая картинка — 404."""
    column = UserImage.thumb if size is PhotoSize.THUMB else UserImage.data
    row = session.execute(
        select(column, UserImage.content_type)
        .join(User, User.id == UserImage.user_id)
        .where(
            UserImage.id == image_id,
            UserImage.user_id == user_id,
            or_(User.avatar_id == image_id, User.cover_id == image_id),
        )
    ).first()
    if row is None:
        raise AppError(404, "image_not_found", "Картинка не найдена")
    data, content_type = row
    return data, THUMB_CONTENT_TYPE if size is PhotoSize.THUMB else content_type
