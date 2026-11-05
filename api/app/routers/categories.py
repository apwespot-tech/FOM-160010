import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, Response, UploadFile, status

from app.deps import AdminUser, CurrentUser, SessionDep
from app.models.event import PHOTO_CONTENT_TYPES
from app.routers.events import PHOTO_HEADERS
from app.schemas.dictionary import CategoryCreate, CategoryUpdate
from app.schemas.event import CategoryOut
from app.services import dictionary_service, event_service, photo_service
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


@router.post("", status_code=status.HTTP_201_CREATED)
def create_category(
    data: Annotated[CategoryCreate, Form()],
    file: Annotated[UploadFile, File(description="Картинка: JPEG, PNG или WebP до 2 МБ")],
    _: AdminUser,
    session: SessionDep,
) -> CategoryOut:
    """Новая категория встаёт в конец справочника (порядок — по id)."""
    category = dictionary_service.create_category(session, data, file.file)
    return CategoryOut.model_validate(category)


@router.patch("/{category_id}")
def update_category(
    category_id: int, body: CategoryUpdate, _: AdminUser, session: SessionDep
) -> CategoryOut:
    return CategoryOut.model_validate(
        dictionary_service.update_category(session, category_id, body)
    )


@router.put("/{category_id}/cover")
def replace_category_cover(
    category_id: int,
    file: Annotated[UploadFile, File(description="JPEG, PNG или WebP до 2 МБ")],
    _: AdminUser,
    session: SessionDep,
) -> CategoryOut:
    """Новая картинка — новый cover_id и адрес; прежняя удаляется."""
    category = dictionary_service.replace_category_cover(session, category_id, file.file)
    return CategoryOut.model_validate(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, _: AdminUser, session: SessionDep) -> Response:
    """Категорию с мероприятиями (в том числе прошедшими) удалить нельзя — 409 category_in_use."""
    dictionary_service.delete_category(session, category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
