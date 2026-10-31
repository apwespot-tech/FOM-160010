import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    SmallInteger,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

MIN_AGE_VALUES = (0, 14, 16, 18)
MIN_PARTICIPANTS = 2
MAX_PARTICIPANTS = 100
MAX_DURATION_MINUTES = 1440


class Category(Base):
    """Справочник категорий; пополняется миграциями."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)


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
