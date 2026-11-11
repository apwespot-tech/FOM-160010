"""Уведомления пользователя внутри приложения.

Функции `notify_*` только добавляют строки в сессию и не коммитят: их вызывает
`event_service` под блокировкой мероприятия перед своим `commit`, поэтому
уведомления атомарны с действием. Напоминания об окне отзывов создаёт фоновый
процесс (`app.worker`).
"""

import uuid
from collections.abc import Iterable, Sequence
from datetime import datetime

from sqlalchemy import DateTime, func, insert, literal, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, aliased

from app.models import Event, EventParticipant, Notification, NotificationType, User
from app.models.notification import notification_type_enum
from app.schemas.notification import (
    NotificationEventRef,
    NotificationList,
    NotificationOut,
    NotificationParticipant,
)
from app.services.review_service import REVIEWS_CLOSE_AFTER, REVIEWS_OPEN_AFTER

LIST_LIMIT = 20

# Поля мероприятия, изменение которых порождает уведомление, — в порядке перечисления
NOTIFY_FIELDS = ("starts_at", "duration_minutes", "city_id", "place", "title")


# --- уведомления о действиях ---


def notify_event_changed(
    session: Session, now: datetime, event: Event, actor: User, changed_fields: Sequence[str]
) -> None:
    _add(
        session,
        now,
        event,
        NotificationType.EVENT_CHANGED,
        _participants_except(session, event.id, actor.id),
        changed_fields=list(changed_fields),
    )


def notify_event_deleted(session: Session, now: datetime, event: Event, actor: User) -> None:
    """Вызывается до удаления мероприятия: получатели читаются из записей участников."""
    _add(
        session,
        now,
        event,
        NotificationType.EVENT_DELETED,
        _participants_except(session, event.id, actor.id),
    )


def notify_participant_removed(
    session: Session, now: datetime, event: Event, actor: User, participant_id: uuid.UUID
) -> None:
    recipients = [participant_id]
    if actor.id != event.organizer_id:
        recipients.append(event.organizer_id)
    _add(
        session,
        now,
        event,
        NotificationType.PARTICIPANT_REMOVED,
        recipients,
        participant_id=participant_id,
    )


def notify_participant_joined(
    session: Session, now: datetime, event: Event, participant_id: uuid.UUID
) -> None:
    _add(
        session,
        now,
        event,
        NotificationType.PARTICIPANT_JOINED,
        [event.organizer_id],
        participant_id=participant_id,
    )


def notify_participant_left(
    session: Session, now: datetime, event: Event, participant_id: uuid.UUID
) -> None:
    _add(
        session,
        now,
        event,
        NotificationType.PARTICIPANT_LEFT,
        [event.organizer_id],
        participant_id=participant_id,
    )


def _participants_except(
    session: Session, event_id: uuid.UUID, actor_id: uuid.UUID
) -> list[uuid.UUID]:
    return list(
        session.scalars(
            select(EventParticipant.user_id).where(
                EventParticipant.event_id == event_id, EventParticipant.user_id != actor_id
            )
        )
    )


def _add(
    session: Session,
    now: datetime,
    event: Event,
    type_: NotificationType,
    recipients: Iterable[uuid.UUID],
    *,
    participant_id: uuid.UUID | None = None,
    changed_fields: list[str] | None = None,
) -> None:
    rows = [
        {
            "user_id": user_id,
            "type": type_,
            "event_id": event.id,
            "event_title": event.title,
            "participant_id": participant_id,
            "changed_fields": changed_fields,
            "created_at": now,
        }
        for user_id in recipients
    ]
    if rows:
        session.execute(insert(Notification), rows)


# --- напоминание об окне отзывов ---


def create_review_reminders(session: Session, now: datetime) -> int:
    """Создаёт напоминания по мероприятиям с открытым окном отзывов и коммитит.

    Повторные и одновременные прогоны не создают дублей: конфликт по уникальному
    индексу пропускается. Возвращает число созданных напоминаний.
    """
    other = aliased(EventParticipant)
    has_others = (
        select(func.count()).select_from(other).where(other.event_id == Event.id).scalar_subquery()
        >= 2
    )
    source = (
        select(
            func.gen_random_uuid(),
            EventParticipant.user_id,
            literal(NotificationType.REVIEW_REMINDER, notification_type_enum),
            Event.id,
            Event.title,
            literal(now, DateTime(timezone=True)),
        )
        .join(EventParticipant, EventParticipant.event_id == Event.id)
        .where(
            Event.starts_at + REVIEWS_OPEN_AFTER <= now,
            Event.starts_at + REVIEWS_CLOSE_AFTER > now,
            has_others,
        )
    )
    statement = (
        pg_insert(Notification)
        .from_select(["id", "user_id", "type", "event_id", "event_title", "created_at"], source)
        .on_conflict_do_nothing(
            index_elements=["user_id", "event_id"],
            index_where=Notification.type == NotificationType.REVIEW_REMINDER,
        )
        .returning(Notification.id)
    )
    created = len(session.execute(statement).all())
    session.commit()
    return created


# --- чтение и отметка ---


def list_notifications(session: Session, user: User) -> NotificationList:
    rows = session.execute(
        select(Notification, User.name)
        .outerjoin(User, User.id == Notification.participant_id)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(LIST_LIMIT)
    ).all()
    return NotificationList(
        items=[_to_out(notification, name) for notification, name in rows],
        unread_count=unread_count(session, user),
    )


def unread_count(session: Session, user: User) -> int:
    count = session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
    )
    return count or 0


def mark_read(session: Session, now: datetime, user: User, up_to: datetime) -> None:
    session.execute(
        update(Notification)
        .where(
            Notification.user_id == user.id,
            Notification.read_at.is_(None),
            Notification.created_at <= up_to,
        )
        .values(read_at=now)
    )
    session.commit()


def _to_out(notification: Notification, participant_name: str | None) -> NotificationOut:
    participant = None
    if notification.participant_id is not None:
        participant = NotificationParticipant(
            id=notification.participant_id, name=participant_name or ""
        )
    return NotificationOut(
        id=notification.id,
        type=notification.type,
        created_at=notification.created_at,
        read=notification.read_at is not None,
        event=NotificationEventRef(id=notification.event_id, title=notification.event_title),
        participant=participant,
        changed_fields=notification.changed_fields,
    )
