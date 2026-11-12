from fastapi import APIRouter, Response, status
from sqlalchemy import select

from app.deps import AdminUser, CurrentUser, SessionDep
from app.models import City
from app.schemas.city import CityOut
from app.schemas.dictionary import CityWrite
from app.services import dictionary_service

router = APIRouter(prefix="/cities", tags=["cities"])


@router.get("")
def list_cities(_: CurrentUser, session: SessionDep) -> list[CityOut]:
    """Справочник городов по алфавиту; меняют миграции и администратор."""
    cities = session.scalars(select(City).order_by(City.name)).all()
    return [CityOut.model_validate(city) for city in cities]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_city(body: CityWrite, _: AdminUser, session: SessionDep) -> CityOut:
    return CityOut.model_validate(dictionary_service.create_city(session, body))


@router.patch("/{city_id}")
def rename_city(city_id: int, body: CityWrite, _: AdminUser, session: SessionDep) -> CityOut:
    return CityOut.model_validate(dictionary_service.rename_city(session, city_id, body))


@router.delete("/{city_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_city(city_id: int, _: AdminUser, session: SessionDep) -> Response:
    """Город с мероприятиями (в том числе прошедшими) удалить нельзя — 409 city_in_use."""
    dictionary_service.delete_city(session, city_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
