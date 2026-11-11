import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.review import EVENT_TITLE_MAX_LENGTH

REVIEW_REMINDER_UNIQUE_INDEX = "uq_notifications_review_reminder"


class NotificationType(enum.StrEnum):
    EVENT_CHANGED = "event_changed"
    EVENT_DELETED = "event_deleted"
    PARTICIPANT_REMOVED = "participant_removed"
    PARTICIPANT_JOINED = "participant_joined"
    PARTICIPANT_LEFT = "participant_left"
    REVIEW_REMINDER = "review_reminder"


# Типы, в которых уведомление указывает участника
PARTICIPANT_TYPES = (
    NotificationType.PARTICIPANT_REMOVED,
    NotificationType.PARTICIPANT_JOINED,
    NotificationType.PARTICIPANT_LEFT,
)

notification_type_enum = Enum(
    NotificationType,
    name="notification_type",
    values_callable=lambda types: [t.value for t in types],
)

_participant_types_sql = ", ".join(f"'{t.value}'" for t in PARTICIPANT_TYPES)


class Notification(Base):
    """Уведомление пользователя внутри приложения. Переживает удаление мероприятия:
    `event_id` становится NULL, название остаётся в `event_title`."""

    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            f"(type IN ({_participant_types_sql})) = (participant_id IS NOT NULL)",
            name="participant_by_type",
        ),
        CheckConstraint(
            "(type = 'event_changed') = (changed_fields IS NOT NULL)",
            name="changed_fields_by_type",
        ),
        Index(
            "ix_notifications_user_created",
            "user_id",
            sql_text("created_at DESC"),
            sql_text("id DESC"),
        ),
        Index(
            "ix_notifications_user_unread",
            "user_id",
            postgresql_where=sql_text("read_at IS NULL"),
        ),
        # Напоминание об окне отзывов — не больше одного на пользователя и мероприятие
        Index(
            REVIEW_REMINDER_UNIQUE_INDEX,
            "user_id",
            "event_id",
            unique=True,
            postgresql_where=sql_text("type = 'review_reminder'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=sql_text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[NotificationType] = mapped_column(notification_type_enum)
    event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("events.id", ondelete="SET NULL"))
    event_title: Mapped[str] = mapped_column(String(EVENT_TITLE_MAX_LENGTH))
    participant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    changed_fields: Mapped[list[str] | None] = mapped_column(ARRAY(String(32)))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
