import uuid
from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict

from app.models import NotificationType


class NotificationEventRef(BaseModel):
    """Мероприятие уведомления; id = null, если мероприятие удалено."""

    id: uuid.UUID | None
    # Название на момент создания уведомления
    title: str


class NotificationParticipant(BaseModel):
    id: uuid.UUID
    # Текущее имя пользователя
    name: str


class NotificationOut(BaseModel):
    id: uuid.UUID
    type: NotificationType
    created_at: datetime
    read: bool
    event: NotificationEventRef
    # Для participant_removed, participant_joined и participant_left, иначе null
    participant: NotificationParticipant | None
    # Для event_changed, иначе null
    changed_fields: list[str] | None


class NotificationList(BaseModel):
    items: list[NotificationOut]
    unread_count: int


class UnreadCount(BaseModel):
    unread_count: int


class MarkRead(BaseModel):
    """Отметить прочитанными уведомления, созданные не позже `up_to`."""

    model_config = ConfigDict(extra="forbid")

    up_to: AwareDatetime
