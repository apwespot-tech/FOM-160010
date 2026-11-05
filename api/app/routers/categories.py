import uuid

from fastapi import APIRouter, Response

from app.deps import CurrentUser, SessionDep
from app.models.event import PHOTO_CONTENT_TYPES
from app.routers.events import PHOTO_HEADERS
from app.schemas.event import CategoryOut
from app.services import event_service, photo_service
from app.services.photo_service import PhotoSize

router = APIRouter(prefix="/categories", tags=["events"])


@router.get("")
def list_categories(_: CurrentUser, session: SessionDep) -> list[CategoryOut]:
    return [CategoryOut.model_validate(c) for c in event_service.list_categories(session)]


@router.get(
    "/{category_id}/covers/{cover_id}",
    response_class=Response,
    responses={200: {"content": {content_type: {} for content_type in PHOTO_CONTENT_TYPES}}},
)
def get_category_cover(
    category_id: int,
    cover_id: uuid.UUID,
    _: CurrentUser,
    session: SessionDep,
    size: PhotoSize = PhotoSize.FULL,
) -> Response:
    """Картинка категории; новая картинка — новый cover_id и новый адрес, кеш бессрочный."""
    data, content_type = photo_service.get_category_cover(session, category_id, cover_id, size)
    return Response(content=data, media_type=content_type, headers=PHOTO_HEADERS)
