import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.models.review import MAX_STARS, MIN_STARS, REVIEW_TEXT_MAX_LENGTH, Review, ReviewKind

Stars = Annotated[int, Field(strict=True, ge=MIN_STARS, le=MAX_STARS)]
ReviewText = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=REVIEW_TEXT_MAX_LENGTH)
]
Anonymous = Annotated[bool, Field(strict=True)]


def _blank_to_none(value: str | None) -> str | None:
    return value or None


class ReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: uuid.UUID
    stars: Stars
    text: ReviewText | None = None
    anonymous: Anonymous = False

    _blank_text = field_validator("text")(_blank_to_none)


class ReviewUpdate(BaseModel):
    """Частичное изменение своего отзыва; очистить значением null можно только текст."""

    model_config = ConfigDict(extra="forbid")

    stars: Stars | None = None
    text: ReviewText | None = None
    anonymous: Anonymous | None = None

    _blank_text = field_validator("text")(_blank_to_none)

    @model_validator(mode="after")
    def required_fields_not_cleared(self) -> Self:
        for field in self.model_fields_set - {"text"}:
            if getattr(self, field) is None:
                raise ValueError(f"Поле {field} нельзя очистить")
        return self


class ReviewEventRef(BaseModel):
    """Мероприятие отзыва; id = null, если мероприятие удалено."""

    id: uuid.UUID | None
    title: str


class ReviewAuthor(BaseModel):
    """Автор без контактов."""

    id: uuid.UUID
    name: str
    avatar_id: uuid.UUID | None


class ReviewOut(BaseModel):
    id: uuid.UUID
    event: ReviewEventRef
    target_id: uuid.UUID
    kind: ReviewKind
    stars: int
    text: str | None
    anonymous: bool
    # null для анонимного отзыва, если смотрит не администратор и не сам автор
    author: ReviewAuthor | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def build(cls, review: Review, author: ReviewAuthor, *, show_author: bool) -> "ReviewOut":
        return cls(
            id=review.id,
            event=ReviewEventRef(id=review.event_id, title=review.event_title),
            target_id=review.target_id,
            kind=review.kind,
            stars=review.stars,
            text=review.text,
            anonymous=review.anonymous,
            author=author if show_author else None,
            created_at=review.created_at,
            updated_at=review.updated_at,
        )


class MyReviews(BaseModel):
    """Свои отзывы по мероприятию и границы окна отзывов."""

    items: list[ReviewOut]
    opens_at: datetime
    closes_at: datetime


class ReviewPage(BaseModel):
    items: list[ReviewOut]
    total: int


class RatingOut(BaseModel):
    """Средняя оценка (null, если отзывов меньше трёх) и число отзывов."""

    average: float | None
    count: int


class ProfileRatings(BaseModel):
    as_organizer: RatingOut
    as_participant: RatingOut


def rating_value(value: Decimal | float | None) -> float | None:
    return float(value) if value is not None else None
