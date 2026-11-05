"""Изменение справочников категорий и городов администратором."""

from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from app.models.city import CITY_NAME_MAX_LENGTH
from app.models.event import CATEGORY_NAME_MAX_LENGTH, ICON_PATTERN

CategoryName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=CATEGORY_NAME_MAX_LENGTH)
]
CityName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=CITY_NAME_MAX_LENGTH)
]
Icon = Annotated[str, StringConstraints(pattern=ICON_PATTERN)]


class CategoryCreate(BaseModel):
    """Поля новой категории (multipart вместе с файлом картинки)."""

    name: CategoryName
    icon: Icon


class CategoryUpdate(BaseModel):
    """Частичное изменение категории; очистить поля нельзя, неизвестные поля — 422."""

    model_config = ConfigDict(extra="forbid")

    name: CategoryName | None = None
    icon: Icon | None = None

    @model_validator(mode="after")
    def fields_not_cleared(self) -> Self:
        for field in ("name", "icon"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"Поле {field} нельзя очистить")
        return self


class CityWrite(BaseModel):
    """Название нового или переименованного города; неизвестные поля — 422."""

    model_config = ConfigDict(extra="forbid")

    name: CityName
