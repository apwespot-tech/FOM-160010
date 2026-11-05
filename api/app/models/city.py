from sqlalchemy import Identity, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

CITY_NAME_MAX_LENGTH = 60
CITY_NAME_UNIQUE_INDEX = "uq_cities_name_lower"


class City(Base):
    """Справочник городов профилей и мероприятий; меняют миграции и администратор."""

    __tablename__ = "cities"
    # Название уникально без учёта регистра
    __table_args__ = (Index(CITY_NAME_UNIQUE_INDEX, func.lower(text("name")), unique=True),)

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    name: Mapped[str] = mapped_column(String(CITY_NAME_MAX_LENGTH))
