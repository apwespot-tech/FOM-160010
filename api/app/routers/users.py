import uuid

from fastapi import APIRouter, Response

from app.deps import CurrentUser, SessionDep
from app.models.event import PHOTO_CONTENT_TYPES
from app.routers.events import PHOTO_HEADERS
from app.services import profile_image_service
from app.services.photo_service import PhotoSize

router = APIRouter(prefix="/users", tags=["profile"])


@router.get(
    "/{user_id}/images/{image_id}",
    response_class=Response,
    responses={200: {"content": {content_type: {} for content_type in PHOTO_CONTENT_TYPES}}},
)
def get_user_image(
    user_id: uuid.UUID,
    image_id: uuid.UUID,
    _: CurrentUser,
    session: SessionDep,
    size: PhotoSize = PhotoSize.FULL,
) -> Response:
    """Аватар или обложка. Доступ шире, чем к профилю: аватар организатора виден в мероприятии
    и незаписанным; id картинки приходит только в ответах, которые зритель вправе получить."""
    data, content_type = profile_image_service.get_image(session, user_id, image_id, size)
    return Response(content=data, media_type=content_type, headers=PHOTO_HEADERS)
