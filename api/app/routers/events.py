import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Event, EventParticipant, User
from app.schemas import EventCreate, EventDetail, EventOut, EventUpdate, UserOut

router = APIRouter(prefix="/events", tags=["events"])


def _to_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _unique_code(db: Session) -> str:
    while True:
        code = secrets.token_urlsafe(6)
        if db.scalar(select(Event.id).where(Event.invite_code == code)) is None:
            return code


def _participants_count(db: Session, event_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(EventParticipant)
        .where(EventParticipant.event_id == event_id)
    )


def _to_out(event: Event, count: int) -> EventOut:
    out = EventOut.model_validate(event)
    out.participants_count = count
    return out


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(
    data: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = Event(
        title=data.title.strip(),
        description=data.description.strip(),
        event_date=_to_naive_utc(data.event_date),
        invite_code=_unique_code(db),
        owner_id=current_user.id,
    )
    db.add(event)
    db.flush()
    db.add(EventParticipant(event_id=event.id, user_id=current_user.id))
    db.commit()
    db.refresh(event)
    return _to_out(event, 1)


@router.get("", response_model=list[EventOut])
def my_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    counts = (
        select(EventParticipant.event_id, func.count().label("cnt"))
        .group_by(EventParticipant.event_id)
        .subquery()
    )
    rows = db.execute(
        select(Event, counts.c.cnt)
        .join(EventParticipant, EventParticipant.event_id == Event.id)
        .join(counts, counts.c.event_id == Event.id)
        .where(EventParticipant.user_id == current_user.id)
        .order_by(Event.event_date.desc())
    ).all()
    return [_to_out(event, cnt) for event, cnt in rows]


@router.get("/{event_id}", response_model=EventDetail)
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Вечер не найден")

    participants = db.scalars(
        select(User)
        .join(EventParticipant, EventParticipant.user_id == User.id)
        .where(EventParticipant.event_id == event_id)
        .order_by(EventParticipant.joined_at)
    ).all()
    if current_user.id not in {user.id for user in participants}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Вы не участник этого вечера")

    detail = EventDetail.model_validate(event)
    detail.participants_count = len(participants)
    detail.participants = [UserOut.model_validate(user) for user in participants]
    return detail


@router.post("/join/{code}", response_model=EventOut)
def join_event(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = db.scalar(select(Event).where(Event.invite_code == code))
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Неверный код приглашения")

    if db.get(EventParticipant, (event.id, current_user.id)) is None:
        db.add(EventParticipant(event_id=event.id, user_id=current_user.id))
        db.commit()

    return _to_out(event, _participants_count(db, event.id))

@router.patch("/{event_id}", response_model=EventOut)
def update_event(
    event_id: int,
    data: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Вечер не найден")
    if event.owner_id != current_user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Изменять вечер может только организатор"
        )

    if data.title is not None:
        event.title = data.title
    if data.description is not None:
        event.description = data.description
    if data.event_date is not None:
        event.event_date = _to_naive_utc(data.event_date)

    db.commit()
    db.refresh(event)
    return _to_out(event, _participants_count(db, event.id))


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Вечер не найден")
    if event.owner_id != current_user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Удалить вечер может только организатор"
        )
    db.delete(event)
    db.commit()