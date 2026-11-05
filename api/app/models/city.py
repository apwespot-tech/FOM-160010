from sqlalchemy import Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class City(Base):
    """Справочник городов профилей и мероприятий; пополняется миграциями."""

    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
