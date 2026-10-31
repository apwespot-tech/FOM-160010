import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import Row, Select, delete, exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ages import calculate_age
from app.errors import AppError, forbidden, not_found
from app.models import Category, Event, EventParticipant, User
from app.schemas.event import EventCreate, EventUpdate, EventView, ParticipantOut


def event_not_found() -> AppError:
    return not_found("Мероприятие не найдено")


# --- категории ---


def list_categories(session: Session) -> Sequence[Category]:
    return session.scalars(select(Category).order_by(Category.id)).all()


# --- чтение мероприятий ---


def _view_query(viewer_id: uuid.UUID) -> Select[Event, str, str | None, int, bool]:
    """Мероприятие с категорией, именем организатора, числом участников и признаком записи."""
    participants_count = (
        select(func.count())
        .select_from(EventParticipant)
        .where(EventParticipant.event_id == Event.id)
        .correlate(Event)
        .scalar_subquery()
    )
    is_joined = (
        exists()
        .where(EventParticipant.event_id == Event.id, EventParticipant.user_id == viewer_id)
        .correlate(Event)
    )
    return (
        select(Event, Category.name, User.name, participants_count, is_joined)
        .join(Category, Category.id == Event.category_id)
        .join(User, User.id == Event.organizer_id)
    )


def _to_view(row: Row[Event, str, str | None, int, bool]) -> EventView:
    event, category_name, organizer_name, participants_count, is_joined = row
    return EventView(
        event=event,
        category_name=category_name,
        organizer_name=organizer_name or "",
        participants_count=participants_count,
        is_joined=is_joined,
    )


def get_event_view(session: Session, viewer_id: uuid.UUID, event_id: uuid.UUID) -> EventView:
    row = session.execute(_view_query(viewer_id).where(Event.id == event_id)).first()
    if row is None:
        raise event_not_found()
    return _to_view(row)


def list_upcoming_events(
    session: Session,
    now: datetime,
    viewer_id: uuid.UUID,
    *,
    category_id: int | None,
    starts_from: datetime | None,
    starts_to: datetime | None,
    limit: int,
    offset: int,
) -> tuple[list[EventView], int]:
    conditions = [Event.starts_at > now]
    if category_id is not None:
        conditions.append(Event.category_id == category_id)
    if starts_from is not None:
        conditions.append(Event.starts_at >= starts_from)
    if starts_to is not None:
        conditions.append(Event.starts_at < starts_to)

    total = session.scalar(select(func.count()).select_from(Event).where(*conditions)) or 0
    rows = session.execute(
        _view_query(viewer_id)
        .where(*conditions)
        .order_by(Event.starts_at, Event.id)
        .limit(limit)
        .offset(offset)
    )
    return [_to_view(row) for row in rows], total


# --- создание, изменение, удаление ---


def create_event(session: Session, now: datetime, user: User, data: EventCreate) -> uuid.UUID:
    _ensure_future(data.starts_at, now)
    _ensure_category_exists(session, data.category_id)
    event = Event(organizer_id=user.id, **data.model_dump())
    session.add(event)
    session.flush()
    # Организатор сразу записан и занимает одно место
    session.add(EventParticipant(event_id=event.id, user_id=user.id, joined_at=now))
    session.commit()
    return event.id


def update_event(
    session: Session, now: datetime, user: User, event_id: uuid.UUID, data: EventUpdate
) -> None:
    event = _lock_event(session, event_id)
    _ensure_can_manage(event, user)
    _ensure_not_started(event, now)

    fields = data.model_fields_set
    if "starts_at" in fields and data.starts_at is not None:
        _ensure_future(data.starts_at, now)
    if "category_id" in fields and data.category_id is not None:
        _ensure_category_exists(session, data.category_id)
    if (
        "max_participants" in fields
        and data.max_participants is not None
        and data.max_participants < _count_participants(session, event.id)
    ):
        raise AppError(
            409,
            "limit_below_participants",
            "Лимит не может быть меньше числа записавшихся участников",
        )

    for field in fields:
        setattr(event, field, getattr(data, field))
    session.commit()


def delete_event(session: Session, now: datetime, user: User, event_id: uuid.UUID) -> None:
    event = _lock_event(session, event_id)
    _ensure_can_manage(event, user)
    _ensure_not_started(event, now)
    session.delete(event)
    session.commit()


# --- участие ---


def join_event(session: Session, now: datetime, user: User, event_id: uuid.UUID) -> None:
    event = _lock_event(session, event_id)
    _ensure_not_started(event, now)
    if _is_participant(session, event.id, user.id):
        raise AppError(409, "already_joined", "Вы уже записаны на это мероприятие")
    if user.birth_date is None or calculate_age(user.birth_date, now.date()) < event.min_age:
        raise AppError(403, "age_restricted", f"Мероприятие доступно с {event.min_age} лет")
    # Подсчёт под блокировкой строки мероприятия: параллельная запись ждёт, лимит не превышается
    if _count_participants(session, event.id) >= event.max_participants:
        raise AppError(409, "event_full", "Свободных мест нет")

    session.add(EventParticipant(event_id=event.id, user_id=user.id, joined_at=now))
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise AppError(409, "already_joined", "Вы уже записаны на это мероприятие") from exc


def leave_event(session: Session, now: datetime, user: User, event_id: uuid.UUID) -> None:
    event = _lock_event(session, event_id)
    _ensure_not_started(event, now)
    if user.id == event.organizer_id:
        raise organizer_cannot_leave()
    if not _delete_participant(session, event.id, user.id):
        raise AppError(409, "not_joined", "Вы не записаны на это мероприятие")
    session.commit()


def remove_participant(
    session: Session, now: datetime, user: User, event_id: uuid.UUID, participant_id: uuid.UUID
) -> None:
    event = _lock_event(session, event_id)
    _ensure_can_manage(event, user)
    _ensure_not_started(event, now)
    if participant_id == event.organizer_id:
        raise organizer_cannot_leave()
    if not _delete_participant(session, event.id, participant_id):
        raise AppError(404, "participant_not_found", "Пользователь не записан на мероприятие")
    session.commit()


def list_participants(session: Session, viewer: User, event_id: uuid.UUID) -> list[ParticipantOut]:
    """Список для записанных и админа; остальным 403 без раскрытия существования."""
    if not viewer.is_admin:
        if not _is_participant(session, event_id, viewer.id):
            raise forbidden()
    elif session.get(Event, event_id) is None:
        raise event_not_found()

    rows = session.execute(
        select(User.id, User.name)
        .join(EventParticipant, EventParticipant.user_id == User.id)
        .join(Event, Event.id == EventParticipant.event_id)
        .where(EventParticipant.event_id == event_id)
        # Организатор первым, даже если записи пришлись на одну и ту же метку времени
        .order_by(User.id != Event.organizer_id, EventParticipant.joined_at, User.id)
    )
    return [ParticipantOut(id=user_id, name=name or "") for user_id, name in rows]


# --- вспомогательное ---


def organizer_cannot_leave() -> AppError:
    return AppError(409, "organizer_cannot_leave", "Организатор не может покинуть своё мероприятие")


def _lock_event(session: Session, event_id: uuid.UUID) -> Event:
    """Строка мероприятия под FOR UPDATE: все изменения одного мероприятия идут по очереди."""
    event = session.scalar(select(Event).where(Event.id == event_id).with_for_update())
    if event is None:
        raise event_not_found()
    return event


def _ensure_can_manage(event: Event, user: User) -> None:
    if event.organizer_id != user.id and not user.is_admin:
        raise forbidden()


def _ensure_not_started(event: Event, now: datetime) -> None:
    if event.starts_at <= now:
        raise AppError(409, "event_started", "Мероприятие уже началось")


def _ensure_future(starts_at: datetime, now: datetime) -> None:
    if starts_at <= now:
        raise AppError(422, "starts_at_in_past", "Дата и время начала должны быть в будущем")


def _ensure_category_exists(session: Session, category_id: int) -> None:
    if session.get(Category, category_id) is None:
        raise AppError(422, "category_not_found", "Категория не найдена")


def _count_participants(session: Session, event_id: uuid.UUID) -> int:
    count = session.scalar(
        select(func.count())
        .select_from(EventParticipant)
        .where(EventParticipant.event_id == event_id)
    )
    return count or 0


def _is_participant(session: Session, event_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    return session.get(EventParticipant, (event_id, user_id)) is not None


def _delete_participant(session: Session, event_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    deleted = session.execute(
        delete(EventParticipant)
        .where(EventParticipant.event_id == event_id, EventParticipant.user_id == user_id)
        .returning(EventParticipant.user_id)
    ).first()
    return deleted is not None
