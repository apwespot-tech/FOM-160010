from fastapi import APIRouter
from sqlalchemy import select

from app.deps import CompletedUser, SessionDep
from app.models import City
from app.schemas.city import CityOut

router = APIRouter(prefix="/cities", tags=["cities"])


@router.get("")
def list_cities(_: CompletedUser, session: SessionDep) -> list[CityOut]:
    """Справочник городов по алфавиту; пополняется миграциями."""
    cities = session.scalars(select(City).order_by(City.name)).all()
    return [CityOut.model_validate(city) for city in cities]
