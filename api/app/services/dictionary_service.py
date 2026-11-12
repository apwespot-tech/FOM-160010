"""Справочники категорий и городов: изменения администратором.

Ссылки на справочники (мероприятия, профили, интересы) защищает БД внешними ключами.
Сервис проверяет «используется ли запись» заранее для понятного ответа, а гонку с одновременной
ссылкой ловит по нарушению внешнего ключа при фиксации транзакции.
"""

from typing import BinaryIO

from sqlalchemy import delete, exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Category, CategoryCover, City, Event
from app.models.city import CITY_NAME_UNIQUE_INDEX
from app.models.event import CATEGORY_NAME_UNIQUE_INDEX
from app.schemas.dictionary import CategoryCreate, CategoryUpdate, CityWrite
from app.services.photo_processing import ProcessedPhoto, process_photo, read_limited

EVENTS_CATEGORY_FK = "fk_events_category_id_categories"
EVENTS_CITY_FK = "fk_events_city_id_cities"
USERS_CITY_FK = "fk_users_city_id_cities"
INTERESTS_CATEGORY_FK = "fk_user_interests_category_id_categories"


def constraint_name(exc: IntegrityError) -> str | None:
    name: str | None = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    return name


def category_not_found() -> AppError:
    return AppError(404, "category_not_found", "Категория не найдена")


def city_not_found() -> AppError:
    return AppError(404, "city_not_found", "Город не найден")


def category_in_use() -> AppError:
    return AppError(409, "category_in_use", "В категории есть мероприятия")


def city_in_use() -> AppError:
    return AppError(409, "city_in_use", "В городе есть мероприятия")


def missing_reference_error(exc: IntegrityError) -> AppError | None:
    """Ссылка на категорию или город, удалённые одновременно с запросом, — как несуществующие."""
    match constraint_name(exc):
        case name if name in (EVENTS_CATEGORY_FK, INTERESTS_CATEGORY_FK):
            return AppError(422, "category_not_found", "Категория не найдена")
        case name if name in (EVENTS_CITY_FK, USERS_CITY_FK):
            return AppError(422, "city_not_found", "Город не найден")
    return None


def _commit(session: Session) -> None:
    """Фиксирует изменение справочника, переводя нарушения ограничений в ответы API."""
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        match constraint_name(exc):
            case name if name == CATEGORY_NAME_UNIQUE_INDEX:
                raise AppError(
                    409, "category_name_taken", "Категория с таким названием уже есть"
                ) from exc
            case name if name == CITY_NAME_UNIQUE_INDEX:
                raise AppError(409, "city_name_taken", "Город с таким названием уже есть") from exc
            # Мероприятие сослалось на запись одновременно с её удалением
            case name if name == EVENTS_CATEGORY_FK:
                raise category_in_use() from exc
            case name if name == EVENTS_CITY_FK:
                raise city_in_use() from exc
        raise


# --- категории ---


def _lock_category(session: Session, category_id: int) -> Category:
    """Строка категории под FOR UPDATE: замены картинки и удаление идут по очереди."""
    category = session.scalar(
        select(Category)
        .where(Category.id == category_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if category is None:
        raise category_not_found()
    return category


def _new_cover(session: Session, photo: ProcessedPhoto) -> CategoryCover:
    cover = CategoryCover(content_type=photo.content_type, data=photo.data, thumb=photo.thumb)
    session.add(cover)
    session.flush()
    return cover


def create_category(session: Session, data: CategoryCreate, stream: BinaryIO) -> Category:
    photo = process_photo(read_limited(stream, 0), 0)
    cover = _new_cover(session, photo)
    category = Category(name=data.name, icon=data.icon, cover_id=cover.id)
    session.add(category)
    _commit(session)
    return category


def update_category(session: Session, category_id: int, data: CategoryUpdate) -> Category:
    category = _lock_category(session, category_id)
    if data.name is not None:
        category.name = data.name
    if data.icon is not None:
        category.icon = data.icon
    _commit(session)
    return category


def replace_category_cover(session: Session, category_id: int, stream: BinaryIO) -> Category:
    """Новая картинка — новый cover_id; прежняя удаляется в той же транзакции."""
    # Проверка и пересохранение файла — до блокировки строки категории
    photo = process_photo(read_limited(stream, 0), 0)
    category = _lock_category(session, category_id)
    previous = category.cover_id
    cover = _new_cover(session, photo)
    category.cover_id = cover.id
    session.flush()
    session.execute(delete(CategoryCover).where(CategoryCover.id == previous))
    _commit(session)
    return category


def delete_category(session: Session, category_id: int) -> None:
    """Удаляет неиспользуемую категорию с картинкой; интересы уходят каскадом."""
    category = _lock_category(session, category_id)
    if session.scalar(select(exists().where(Event.category_id == category_id))):
        session.rollback()
        raise category_in_use()
    cover_id = category.cover_id
    session.delete(category)
    session.flush()
    session.execute(delete(CategoryCover).where(CategoryCover.id == cover_id))
    _commit(session)


# --- города ---


def _lock_city(session: Session, city_id: int) -> City:
    city = session.scalar(
        select(City)
        .where(City.id == city_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if city is None:
        raise city_not_found()
    return city


def create_city(session: Session, data: CityWrite) -> City:
    city = City(name=data.name)
    session.add(city)
    _commit(session)
    return city


def rename_city(session: Session, city_id: int, data: CityWrite) -> City:
    city = _lock_city(session, city_id)
    city.name = data.name
    _commit(session)
    return city


def delete_city(session: Session, city_id: int) -> None:
    """Удаляет город без мероприятий; в профилях город очищается (SET NULL)."""
    city = _lock_city(session, city_id)
    if session.scalar(select(exists().where(Event.city_id == city_id))):
        session.rollback()
        raise city_in_use()
    session.delete(city)
    _commit(session)
