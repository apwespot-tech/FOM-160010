import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, Query, Response, UploadFile, status
from pydantic import AwareDatetime

from app.deps import CompletedUser, CurrentUser, NowDep, OrganizerUser, ParticipantUser, SessionDep
from app.models.event import MAX_PARTICIPANTS, PHOTO_CONTENT_TYPES
from app.schemas.event import EventCreate, EventOut, EventPage, EventUpdate, ParticipantOut
from app.services import event_service, photo_service
from app.services.event_service import EventPeriod, EventScope
from app.services.photo_service import PhotoSize

router = APIRouter(prefix="/events", tags=["events"])

PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MAX_SEARCH_LENGTH = 100
PHOTO_HEADERS = {
    "Cache-Control": "private, max-age=31536000, immutable",
    "X-Content-Type-Options": "nosniff",
}


@router.get("")
def list_events(
    user: CurrentUser,
    session: SessionDep,
    now: NowDep,
    scope: EventScope = EventScope.ALL,
    period: EventPeriod = EventPeriod.UPCOMING,
    min_free_places: Annotated[int | None, Query(ge=1, le=MAX_PARTICIPANTS)] = None,
    category_id: int | None = None,
    starts_from: Annotated[AwareDatetime | None, Query(alias="from")] = None,
    starts_to: Annotated[AwareDatetime | None, Query(alias="to")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = PAGE_SIZE,
    offset: Annotated[int, Query(ge=0)] = 0,
    q: Annotated[str | None, Query(max_length=MAX_SEARCH_LENGTH)] = None,
) -> EventPage:
    views, total = event_service.list_events(
        session,
        now,
        user,
        scope=scope,
        period=period,
        min_free_places=min_free_places,
        category_id=category_id,
        starts_from=starts_from,
        starts_to=starts_to,
        limit=limit,
        offset=offset,
        search=q,
    )
    return EventPage(items=[EventOut.from_view(view) for view in views], total=total)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_event(
    body: EventCreate, user: OrganizerUser, session: SessionDep, now: NowDep
) -> EventOut:
    event_id = event_service.create_event(session, now, user, body)
    return EventOut.from_view(event_service.get_event_view(session, user, event_id))


@router.get("/{event_id}")
def get_event(event_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> EventOut:
    return EventOut.from_view(event_service.get_event_view(session, user, event_id))


@router.patch("/{event_id}")
def update_event(
    event_id: uuid.UUID, body: EventUpdate, user: CompletedUser, session: SessionDep, now: NowDep
) -> EventOut:
    event_service.update_event(session, now, user, event_id, body)
    return EventOut.from_view(event_service.get_event_view(session, user, event_id))


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: uuid.UUID, user: CompletedUser, session: SessionDep, now: NowDep
) -> Response:
    event_service.delete_event(session, now, user, event_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{event_id}/photos/{photo_id}",
    response_class=Response,
    responses={200: {"content": {content_type: {} for content_type in PHOTO_CONTENT_TYPES}}},
)
def get_photo(
    event_id: uuid.UUID,
    photo_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
    size: PhotoSize = PhotoSize.FULL,
) -> Response:
    data, content_type = photo_service.get_photo(session, event_id, photo_id, size)
    # Фото с данным id никогда не меняется: браузер хранит его бессрочно, общие кеши — нет
    return Response(content=data, media_type=content_type, headers=PHOTO_HEADERS)


@router.put("/{event_id}/photos")
def replace_photos(
    event_id: uuid.UUID,
    user: CompletedUser,
    session: SessionDep,
    now: NowDep,
    order: Annotated[str, Form(description='JSON: [{"id": "<uuid>"} | {"file": n}, ...]')],
    files: Annotated[list[UploadFile] | None, File(description="Новые файлы фото")] = None,
) -> EventOut:
    """Заменяет набор фото итоговым упорядоченным списком; первое фото — основное."""
    photo_service.replace_photos(
        session, now, user, event_id, order, [upload.file for upload in files or []]
    )
    return EventOut.from_view(event_service.get_event_view(session, user, event_id))


@router.post("/{event_id}/join")
def join_event(
    event_id: uuid.UUID, user: ParticipantUser, session: SessionDep, now: NowDep
) -> EventOut:
    event_service.join_event(session, now, user, event_id)
    return EventOut.from_view(event_service.get_event_view(session, user, event_id))


@router.post("/{event_id}/leave")
def leave_event(
    event_id: uuid.UUID, user: CompletedUser, session: SessionDep, now: NowDep
) -> EventOut:
    event_service.leave_event(session, now, user, event_id)
    return EventOut.from_view(event_service.get_event_view(session, user, event_id))


@router.get("/{event_id}/participants")
def list_participants(
    event_id: uuid.UUID, user: CompletedUser, session: SessionDep
) -> list[ParticipantOut]:
    return event_service.list_participants(session, user, event_id)


@router.post("/{event_id}/participants/{user_id}/remove")
def remove_participant(
    event_id: uuid.UUID,
    user_id: uuid.UUID,
    user: CompletedUser,
    session: SessionDep,
    now: NowDep,
) -> EventOut:
    event_service.remove_participant(session, now, user, event_id, user_id)
    return EventOut.from_view(event_service.get_event_view(session, user, event_id))
