import uuid
from datetime import date
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, EmailStr, HttpUrl, StringConstraints, model_validator

from app.ages import calculate_age
from app.models import Role, User
from app.phones import Phone

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Telegram = Annotated[str, StringConstraints(pattern=r"^@[A-Za-z0-9_]{5,32}$")]

REQUIRED_FIELDS = ("name", "birth_date")


class ProfileOut(BaseModel):
    id: uuid.UUID
    phone: str
    name: str | None
    birth_date: date | None
    age: int | None
    email: str | None
    telegram: str | None
    photo_url: str | None
    roles: list[Role]
    profile_completed: bool

    @classmethod
    def from_user(cls, user: User, today: date) -> "ProfileOut":
        return cls(
            id=user.id,
            phone=user.phone,
            name=user.name,
            birth_date=user.birth_date,
            age=calculate_age(user.birth_date, today) if user.birth_date else None,
            email=user.email,
            telegram=user.telegram,
            photo_url=user.photo_url,
            roles=sorted(user.roles),
            profile_completed=user.profile_completed,
        )


class ProfileUpdate(BaseModel):
    """Изменение своего профиля. Неизвестные поля (phone, roles, id) — 422."""

    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    birth_date: date | None = None
    email: EmailStr | None = None
    telegram: Telegram | None = None
    photo_url: HttpUrl | None = None

    @model_validator(mode="after")
    def required_fields_not_cleared(self) -> Self:
        for field in REQUIRED_FIELDS:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"Поле {field} нельзя очистить")
        return self


class AdminProfileUpdate(ProfileUpdate):
    """Изменение чужого профиля администратором: дополнительно можно сменить телефон."""

    phone: Phone | None = None

    @model_validator(mode="after")
    def phone_not_cleared(self) -> Self:
        if "phone" in self.model_fields_set and self.phone is None:
            raise ValueError("Поле phone нельзя очистить")
        return self
