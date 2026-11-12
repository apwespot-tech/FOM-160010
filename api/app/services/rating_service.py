"""Рейтинги пользователей: считаются запросом по отзывам, нигде не хранятся."""

import uuid
from decimal import Decimal

from sqlalchemy import ColumnElement, ScalarSelect, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.models import Review, ReviewKind
from app.schemas.review import ProfileRatings, RatingOut, rating_value

# Рейтинг показывается, только когда отзывов не меньше этого числа
MIN_REVIEWS_FOR_RATING = 3


def _rounded_average() -> ColumnElement[Decimal | None]:
    """Среднее с одним знаком (numeric: половина — от нуля, для оценок это «вверх»)."""
    return func.round(func.avg(Review.stars), 1)


def rating_subquery(
    user_id: InstrumentedAttribute[uuid.UUID], kind: ReviewKind
) -> ScalarSelect[Decimal | None]:
    """Коррелированный подзапрос рейтинга: среднее или NULL, если отзывов меньше трёх."""
    return (
        select(_rounded_average())
        .where(Review.target_id == user_id, Review.kind == kind)
        .having(func.count() >= MIN_REVIEWS_FOR_RATING)
        .correlate_except(Review)
        .scalar_subquery()
    )


def profile_ratings(session: Session, user_id: uuid.UUID) -> ProfileRatings:
    rows = session.execute(
        select(Review.kind, func.count(), _rounded_average())
        .where(Review.target_id == user_id)
        .group_by(Review.kind)
    ).all()
    by_kind: dict[ReviewKind, tuple[int, Decimal | None]] = {
        kind: (count, average) for kind, count, average in rows
    }

    def rating(kind: ReviewKind) -> RatingOut:
        count, average = by_kind.get(kind, (0, None))
        return RatingOut(
            average=rating_value(average) if count >= MIN_REVIEWS_FOR_RATING else None,
            count=count,
        )

    return ProfileRatings(
        as_organizer=rating(ReviewKind.ORGANIZER),
        as_participant=rating(ReviewKind.PARTICIPANT),
    )
