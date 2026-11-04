import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    LargeBinary,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

MIN_AGE_VALUES = (0, 14, 16, 18)
MIN_PARTICIPANTS = 2
MAX_PARTICIPANTS = 100
MAX_DURATION_MINUTES = 1440

MAX_PHOTOS = 10
MAX_PHOTO_BYTES = 2 * 1024 * 1024
PHOTO_CONTENT_TYPES = ("image/jpeg", "image/png", "image/webp")
# Уменьшенные копии фото и картинок категорий — WebP не шире этого значения
THUMB_WIDTH = 800
ICON_PATTERN = "^pi-[a-z0-9-]+$"


class CategoryCover(Base):
    """Картинка категории: полная и уменьшенная копия. Замена картинки — новая строка."""

    __tablename__ = "category_covers"
    __table_args__ = (
        CheckConstraint(
            f"content_type IN ({', '.join(repr(t) for t in PHOTO_CONTENT_TYPES)})",
            name="content_type_values",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    content_type: Mapped[str] = mapped_column(String(20))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    thumb: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Category(Base):
    """Справочник категорий; пополняется миграциями, каждая категория — с иконкой и картинкой."""

    __tablename__ = "categories"
    __table_args__ = (CheckConstraint(f"icon ~ '{ICON_PATTERN}'", name="icon_format"),)

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    icon: Mapped[str] = mapped_column(String(40))
    cover_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("category_covers.id", ondelete="RESTRICT")
    )


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint(
            f"max_participants BETWEEN {MIN_PARTICIPANTS} AND {MAX_PARTICIPANTS}",
            name="max_participants_range",
        ),
        CheckConstraint(
            f"min_age IN ({', '.join(str(age) for age in MIN_AGE_VALUES)})", name="min_age_values"
        ),
        CheckConstraint(
            f"duration_minutes BETWEEN 1 AND {MAX_DURATION_MINUTES}", name="duration_range"
        ),
        Index("ix_events_starts_at", "starts_at", "id"),
        Index("ix_events_category_id_starts_at", "category_id", "starts_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    organizer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(2000))
    place: Mapped[str] = mapped_column(String(200))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    max_participants: Mapped[int] = mapped_column(SmallInteger)
    min_age: Mapped[int] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EventParticipant(Base):
    """Запись на мероприятие. Организатор тоже записан и занимает место."""

    __tablename__ = "event_participants"
    __table_args__ = (Index("ix_event_participants_user_id", "user_id"),)

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EventPhoto(Base):
    """Фото мероприятия: метаданные и порядок. Байты — в EventPhotoData."""

    __tablename__ = "event_photos"
    __table_args__ = (
        CheckConstraint(f"position BETWEEN 0 AND {MAX_PHOTOS - 1}", name="position_range"),
        CheckConstraint(
            f"content_type IN ({', '.join(repr(t) for t in PHOTO_CONTENT_TYPES)})",
            name="content_type_values",
        ),
        # Отложенная уникальность: порядок переставляется в одной транзакции
        UniqueConstraint("event_id", "position", deferrable=True, initially="DEFERRED"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(SmallInteger)
    content_type: Mapped[str] = mapped_column(String(20))
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EventPhotoData(Base):
    """Содержимое фото. Отдельная таблица, чтобы запросы мероприятий не читали байты."""

    __tablename__ = "event_photo_data"

    photo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("event_photos.id", ondelete="CASCADE"), primary_key=True
    )
    data: Mapped[bytes] = mapped_column(LargeBinary)
    # Уменьшенная копия (WebP, ширина <= THUMB_WIDTH) для карточек и миниатюр
    thumb: Mapped[bytes] = mapped_column(LargeBinary)
