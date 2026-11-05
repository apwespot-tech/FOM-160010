import uuid
from datetime import date, datetime
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.ages import calculate_age
from app.models import Role, User
from app.models.user import ABOUT_MAX_LENGTH
from app.phones import Phone
from app.schemas.city import CityOut

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Telegram = Annotated[str, StringConstraints(pattern=r"^@[A-Za-z0-9_]{5,32}$")]
About = Annotated[str, StringConstraints(strip_whitespace=True, max_length=ABOUT_MAX_LENGTH)]

REQUIRED_FIELDS = ("name", "birth_date")


class InterestOut(BaseModel):
    """Интерес — категория мероприятий с иконкой."""

    id: int
    name: str
    icon: str


class ProfileStats(BaseModel):
    # Мероприятия, где пользователь автор (предстоящие и прошедшие)
    organized_count: int
    # Прошедшие чужие мероприятия, на которые пользователь записан
    attended_count: int


class ProfileOut(BaseModel):
    id: uuid.UUID
    phone: str
    name: str | None
    birth_date: date | None
    age: int | None
    email: str | None
    telegram: str | None
    about: str | None
    city: CityOut | None
    interests: list[InterestOut]
    # Картинки профиля: GET /users/{id}/images/{image_id}
    avatar_id: uuid.UUID | None
    cover_id: uuid.UUID | None
    created_at: datetime
    stats: ProfileStats
    roles: list[Role]
    profile_completed: bool

    @classmethod
    def from_user(
        cls,
        user: User,
        today: date,
        *,
        city: CityOut | None,
        interests: list[InterestOut],
        stats: ProfileStats,
    ) -> "ProfileOut":
        return cls(
            id=user.id,
            phone=user.phone,
            name=user.name,
            birth_date=user.birth_date,
            age=calculate_age(user.birth_date, today) if user.birth_date else None,
            email=user.email,
            telegram=user.telegram,
            about=user.about,
            city=city,
            interests=interests,
            avatar_id=user.avatar_id,
            cover_id=user.cover_id,
            created_at=user.created_at,
            stats=stats,
            roles=sorted(user.roles),
            profile_completed=user.profile_completed,
        )


class ProfileUpdate(BaseModel):
    """Изменение своего профиля. Неизвестные поля (phone, roles, id, photo_url) — 422."""

    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    birth_date: date | None = None
    email: EmailStr | None = None
    telegram: Telegram | None = None
    about: About | None = None
    city_id: int | None = None
    # Новый набор интересов целиком; очистка — пустой список
    interest_ids: list[int] | None = None

    @field_validator("about")
    @classmethod
    def blank_about_is_none(cls, value: str | None) -> str | None:
        return value or None

    @field_validator("interest_ids")
    @classmethod
    def interests_unique(cls, value: list[int] | None) -> list[int] | None:
        if value is not None and len(set(value)) != len(value):
            raise ValueError("Категория в интересах указана дважды")
        return value

    @model_validator(mode="after")
    def required_fields_not_cleared(self) -> Self:
        for field in REQUIRED_FIELDS:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"Поле {field} нельзя очистить")
        if "interest_ids" in self.model_fields_set and self.interest_ids is None:
            raise ValueError("Интересы очищаются пустым списком")
        return self


class AdminProfileUpdate(ProfileUpdate):
    """Изменение чужого профиля администратором: дополнительно можно сменить телефон."""

    phone: Phone | None = None

    @model_validator(mode="after")
    def phone_not_cleared(self) -> Self:
        if "phone" in self.model_fields_set and self.phone is None:
            raise ValueError("Поле phone нельзя очистить")
        return self
