import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

MIN_STARS = 1
MAX_STARS = 5
REVIEW_TEXT_MAX_LENGTH = 1000
EVENT_TITLE_MAX_LENGTH = 100
REVIEW_UNIQUE_CONSTRAINT = "uq_reviews_event_author_target"


class ReviewKind(enum.StrEnum):
    """Вид отзыва — по роли получателя на мероприятии."""

    ORGANIZER = "organizer"
    PARTICIPANT = "participant"


review_kind_enum = Enum(
    ReviewKind,
    name="review_kind",
    values_callable=lambda kinds: [kind.value for kind in kinds],
)


class Review(Base):
    """Отзыв о человеке по итогам мероприятия. Переживает удаление мероприятия:
    `event_id` становится NULL, название остаётся в `event_title`."""

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint(f"stars BETWEEN {MIN_STARS} AND {MAX_STARS}", name="stars_range"),
        CheckConstraint("author_id <> target_id", name="not_self"),
        UniqueConstraint("event_id", "author_id", "target_id", name=REVIEW_UNIQUE_CONSTRAINT),
        Index(
            "ix_reviews_target_kind_created",
            "target_id",
            "kind",
            sql_text("created_at DESC"),
            sql_text("id DESC"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=sql_text("gen_random_uuid()")
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("events.id", ondelete="SET NULL"))
    event_title: Mapped[str] = mapped_column(String(EVENT_TITLE_MAX_LENGTH))
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    target_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[ReviewKind] = mapped_column(review_kind_enum)
    stars: Mapped[int] = mapped_column(SmallInteger)
    text: Mapped[str | None] = mapped_column(String(REVIEW_TEXT_MAX_LENGTH))
    anonymous: Mapped[bool] = mapped_column(
        Boolean, server_default=sql_text("false"), default=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
