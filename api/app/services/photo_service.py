"""Фото мероприятий: отдача файла и замена набора целиком."""

import json
import uuid
from datetime import datetime
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Event, EventPhoto, EventPhotoData, User
from app.models.event import MAX_PHOTOS
from app.services.event_service import (
    _ensure_can_manage,
    _ensure_not_started,
    _lock_event,
    event_not_found,
)
from app.services.photo_processing import ProcessedPhoto, process_photo, read_limited

# Элемент итогового порядка: id сохранённого фото или номер нового файла в запросе
OrderItem = uuid.UUID | int


def photo_not_found() -> AppError:
    return AppError(404, "photo_not_found", "Фото не найдено")


def too_many_photos() -> AppError:
    return AppError(422, "too_many_photos", f"Не больше {MAX_PHOTOS} фото")


def photo_list_invalid(message: str) -> AppError:
    return AppError(422, "photo_list_invalid", message)


def get_photo(session: Session, event_id: uuid.UUID, photo_id: uuid.UUID) -> tuple[bytes, str]:
    """Содержимое и тип фото; фото другого мероприятия — как несуществующее."""
    row = session.execute(
        select(EventPhotoData.data, EventPhoto.content_type)
        .join(EventPhoto, EventPhoto.id == EventPhotoData.photo_id)
        .where(EventPhoto.id == photo_id, EventPhoto.event_id == event_id)
    ).first()
    if row is None:
        raise photo_not_found()
    data, content_type = row
    return data, content_type


def parse_order(raw: str, files_count: int) -> list[OrderItem]:
    """Разбирает поле order: [{"id": "<uuid>"} | {"file": n}, ...]."""
    try:
        items = json.loads(raw)
    except ValueError as exc:
        raise photo_list_invalid("Некорректный список фото") from exc
    if not isinstance(items, list):
        raise photo_list_invalid("Некорректный список фото")
    if len(items) > MAX_PHOTOS or files_count > MAX_PHOTOS:
        raise too_many_photos()

    order: list[OrderItem] = []
    seen_ids: set[uuid.UUID] = set()
    seen_files: set[int] = set()
    for item in items:
        if not isinstance(item, dict) or len(item) != 1:
            raise photo_list_invalid("Некорректный элемент списка фото")
        if "id" in item:
            try:
                photo_id = uuid.UUID(str(item["id"]))
            except ValueError as exc:
                raise photo_list_invalid("Некорректный id фото") from exc
            if photo_id in seen_ids:
                raise photo_list_invalid("Фото указано дважды")
            seen_ids.add(photo_id)
            order.append(photo_id)
        elif "file" in item:
            index = item["file"]
            # bool — подкласс int, его не принимаем
            if (
                not isinstance(index, int)
                or isinstance(index, bool)
                or not 0 <= index < files_count
                or index in seen_files
            ):
                raise photo_list_invalid("Некорректная ссылка на файл")
            seen_files.add(index)
            order.append(index)
        else:
            raise photo_list_invalid("Некорректный элемент списка фото")

    if len(seen_files) != files_count:
        raise photo_list_invalid("Каждый загруженный файл должен быть в списке")
    return order


def replace_photos(
    session: Session,
    now: datetime,
    user: User,
    event_id: uuid.UUID,
    order_raw: str,
    files: list[BinaryIO],
) -> None:
    """Заменяет набор фото итоговым списком в одной транзакции под блокировкой мероприятия."""
    # 1. Быстрый отказ до чтения файлов: посторонний не заставит сервер декодировать картинки
    event = session.get(Event, event_id)
    if event is None:
        raise event_not_found()
    _ensure_can_manage(event, user)
    _ensure_not_started(event, now)
    # Не держим транзакцию открытой, пока обрабатываются файлы
    session.rollback()

    # 2–3. Список и файлы — без блокировки строки
    order = parse_order(order_raw, len(files))
    processed: list[ProcessedPhoto] = [
        process_photo(read_limited(stream, index), index) for index, stream in enumerate(files)
    ]

    # 4. Под блокировкой: все изменения мероприятия идут по очереди, проверки — заново
    event = _lock_event(session, event_id)
    _ensure_can_manage(event, user)
    _ensure_not_started(event, now)

    existing = {
        photo.id: photo
        for photo in session.scalars(select(EventPhoto).where(EventPhoto.event_id == event.id))
    }
    # 5. Ссылаться можно только на фото этого мероприятия
    kept = {item for item in order if isinstance(item, uuid.UUID)}
    if not kept <= existing.keys():
        raise photo_list_invalid("Фото не принадлежит мероприятию")

    # 6. Удаление, новый порядок и новые фото; UNIQUE(event_id, position) проверится при коммите
    for photo_id, photo in existing.items():
        if photo_id not in kept:
            session.delete(photo)
    new_data: list[EventPhotoData] = []
    for position, item in enumerate(order):
        if isinstance(item, uuid.UUID):
            existing[item].position = position
            continue
        upload = processed[item]
        photo = EventPhoto(
            id=uuid.uuid4(),
            event_id=event.id,
            position=position,
            content_type=upload.content_type,
            size_bytes=len(upload.data),
            created_at=now,
        )
        session.add(photo)
        new_data.append(EventPhotoData(photo_id=photo.id, data=upload.data))
    session.flush()
    session.add_all(new_data)
    session.commit()
