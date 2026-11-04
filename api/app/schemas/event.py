import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models import Event
from app.models.event import MAX_DURATION_MINUTES, MAX_PARTICIPANTS, MIN_PARTICIPANTS

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Description = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]
Place = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Duration = Annotated[int, Field(ge=1, le=MAX_DURATION_MINUTES)]
MaxParticipants = Annotated[int, Field(ge=MIN_PARTICIPANTS, le=MAX_PARTICIPANTS)]
MinAge = Literal[0, 14, 16, 18]

# Поля, которые в PATCH можно очистить значением null
NULLABLE_FIELDS = frozenset({"duration_minutes"})


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    # Имя иконки primeicons, например pi-video
    icon: str
    # Картинка категории: GET /categories/{id}/covers/{cover_id}
    cover_id: uuid.UUID


class EventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title
    description: Description
    place: Place
    starts_at: AwareDatetime
    duration_minutes: Duration | None = None
    category_id: int
    max_participants: MaxParticipants
    min_age: MinAge


class EventUpdate(BaseModel):
    """Частичное изменение. Неизвестные поля (id, organizer_id) — 422."""

    model_config = ConfigDict(extra="forbid")

    title: Title | None = None
    description: Description | None = None
    place: Place | None = None
    starts_at: AwareDatetime | None = None
    duration_minutes: Duration | None = None
    category_id: int | None = None
    max_participants: MaxParticipants | None = None
    min_age: MinAge | None = None

    @model_validator(mode="after")
    def required_fields_not_cleared(self) -> Self:
        for field in self.model_fields_set - NULLABLE_FIELDS:
            if getattr(self, field) is None:
                raise ValueError(f"Поле {field} нельзя очистить")
        return self


class PersonOut(BaseModel):
    """Человек в мероприятии: без телефона и email."""

    id: uuid.UUID
    name: str
    photo_url: str | None
    telegram: str | None


class OrganizerOut(PersonOut):
    """telegram заполнен только для записанных участников и администратора."""


class ParticipantOut(PersonOut):
    pass


@dataclass(frozen=True)
class EventView:
    """Мероприятие с данными, вычисленными запросом: категория, организатор, участники."""

    event: Event
    category_name: str
    category_icon: str
    category_cover_id: uuid.UUID
    organizer_name: str
    organizer_photo_url: str | None
    organizer_telegram: str | None
    participants_count: int
    is_joined: bool
    # id фото по порядку; первое — основное
    photo_ids: tuple[uuid.UUID, ...] = ()


class PhotoRef(BaseModel):
    """Ссылка на фото мероприятия; содержимое — по GET /events/{id}/photos/{photo_id}."""

    id: uuid.UUID


class EventOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    place: str
    starts_at: datetime
    duration_minutes: int | None
    created_at: datetime
    category: CategoryOut
    max_participants: int
    min_age: int
    organizer: OrganizerOut
    photos: list[PhotoRef]
    participants_count: int
    free_places: int
    is_full: bool
    is_joined: bool

    @classmethod
    def from_view(cls, view: EventView) -> "EventOut":
        event = view.event
        free_places = max(event.max_participants - view.participants_count, 0)
        return cls(
            id=event.id,
            title=event.title,
            description=event.description,
            place=event.place,
            starts_at=event.starts_at,
            duration_minutes=event.duration_minutes,
            created_at=event.created_at,
            category=CategoryOut(
                id=event.category_id,
                name=view.category_name,
                icon=view.category_icon,
                cover_id=view.category_cover_id,
            ),
            max_participants=event.max_participants,
            min_age=event.min_age,
            organizer=OrganizerOut(
                id=event.organizer_id,
                name=view.organizer_name,
                photo_url=view.organizer_photo_url,
                telegram=view.organizer_telegram,
            ),
            photos=[PhotoRef(id=photo_id) for photo_id in view.photo_ids],
            participants_count=view.participants_count,
            free_places=free_places,
            is_full=free_places == 0,
            is_joined=view.is_joined,
        )


class EventPage(BaseModel):
    items: list[EventOut]
    total: int
