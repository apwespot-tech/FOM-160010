"""Отзывы о людях по итогам мероприятия и рейтинги, которые из них считаются."""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import Select, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError, forbidden, not_found
from app.models import Event, EventParticipant, Review, ReviewKind, User
from app.models.review import REVIEW_UNIQUE_CONSTRAINT
from app.schemas.review import (
    MyReviews,
    ReviewAuthor,
    ReviewCreate,
    ReviewOut,
    ReviewPage,
    ReviewUpdate,
)
from app.services import profile_service
from app.services.dictionary_service import constraint_name

# Окно отзывов: [starts_at + 24 ч, starts_at + 8 суток)
REVIEWS_OPEN_AFTER = timedelta(hours=24)
REVIEWS_CLOSE_AFTER = timedelta(days=8)


def review_not_found() -> AppError:
    return not_found("Отзыв не найден")


# --- окно отзывов ---


def review_window(starts_at: datetime) -> tuple[datetime, datetime]:
    return starts_at + REVIEWS_OPEN_AFTER, starts_at + REVIEWS_CLOSE_AFTER


def _ensure_window_open(starts_at: datetime, now: datetime) -> None:
    opens_at, closes_at = review_window(starts_at)
    if now < opens_at:
        raise AppError(
            409, "review_not_open", "Отзыв можно оставить через сутки после начала мероприятия"
        )
    if now >= closes_at:
        raise AppError(409, "review_closed", "Время для отзыва истекло")


def _ensure_author_window(session: Session, review: Review, now: datetime) -> None:
    """Окно для автора; если мероприятие удалено, окно считается закрытым."""
    event = session.get(Event, review.event_id) if review.event_id is not None else None
    if event is None:
        raise AppError(409, "review_closed", "Время для отзыва истекло")
    _ensure_window_open(event.starts_at, now)


# --- представление ---


def _author_of(user: User) -> ReviewAuthor:
    return ReviewAuthor(id=user.id, name=user.name or "", avatar_id=user.avatar_id)


def _show_author(review: Review, viewer: User) -> bool:
    return not review.anonymous or viewer.is_admin or viewer.id == review.author_id


def to_out(session: Session, review: Review, viewer: User) -> ReviewOut:
    """Отзыв для зрителя: автор анонимного отзыва виден только администратору и самому автору."""
    author = session.get(User, review.author_id)
    assert author is not None
    return ReviewOut.build(review, _author_of(author), show_author=_show_author(review, viewer))


ReviewRows = Select[Review, str | None, uuid.UUID | None]


def _review_rows() -> ReviewRows:
    """Отзывы с именем и аватаром автора."""
    return select(Review, User.name, User.avatar_id).join(User, User.id == Review.author_id)


def _with_authors(session: Session, query: ReviewRows, viewer: User) -> list[ReviewOut]:
    return [
        ReviewOut.build(
            review,
            ReviewAuthor(id=review.author_id, name=name or "", avatar_id=avatar_id),
            show_author=_show_author(review, viewer),
        )
        for review, name, avatar_id in session.execute(query)
    ]


# --- создание, изменение, удаление ---


def _is_participant(session: Session, event_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    return session.get(EventParticipant, (event_id, user_id)) is not None


def create_review(
    session: Session, now: datetime, author: User, event_id: uuid.UUID, data: ReviewCreate
) -> Review:
    event = session.get(Event, event_id)
    if event is None:
        raise not_found("Мероприятие не найдено")
    if not _is_participant(session, event_id, author.id):
        raise AppError(403, "not_participant", "Отзыв оставляют только участники мероприятия")
    _ensure_window_open(event.starts_at, now)
    if data.target_id == author.id or not _is_participant(session, event_id, data.target_id):
        raise AppError(
            422, "review_target_invalid", "Оценить можно только другого участника мероприятия"
        )

    review = Review(
        event_id=event.id,
        event_title=event.title,
        author_id=author.id,
        target_id=data.target_id,
        # Организатора мероприятия изменить нельзя, поэтому вид отзыва фиксируется сразу
        kind=ReviewKind.ORGANIZER
        if data.target_id == event.organizer_id
        else ReviewKind.PARTICIPANT,
        stars=data.stars,
        text=data.text,
        anonymous=data.anonymous,
        created_at=now,
        updated_at=now,
    )
    session.add(review)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        if constraint_name(exc) == REVIEW_UNIQUE_CONSTRAINT:
            raise AppError(409, "review_exists", "Вы уже оставили отзыв") from exc
        raise
    return review


def update_review(
    session: Session, now: datetime, user: User, review_id: uuid.UUID, data: ReviewUpdate
) -> Review:
    # Изменения одного отзыва идут по очереди
    review = session.scalar(select(Review).where(Review.id == review_id).with_for_update())
    if review is None:
        raise review_not_found()
    if review.author_id != user.id:
        raise forbidden()
    _ensure_author_window(session, review, now)

    for field in data.model_fields_set:
        setattr(review, field, getattr(data, field))
    review.updated_at = now
    session.commit()
    return review


def delete_review(session: Session, now: datetime, user: User, review_id: uuid.UUID) -> None:
    """Автор удаляет свой отзыв в окне, администратор — любой и в любой момент."""
    review = session.get(Review, review_id)
    if review is None:
        raise review_not_found()
    if not user.is_admin:
        if review.author_id != user.id:
            raise forbidden()
        _ensure_author_window(session, review, now)

    deleted = session.execute(
        delete(Review).where(Review.id == review_id).returning(Review.id)
    ).first()
    if deleted is None:
        session.rollback()
        raise review_not_found()
    session.commit()


# --- чтение ---


def my_reviews(session: Session, viewer: User, event_id: uuid.UUID) -> MyReviews:
    """Свои отзывы по мероприятию; доступ — как к списку участников."""
    if not viewer.is_admin and not _is_participant(session, event_id, viewer.id):
        raise forbidden()
    event = session.get(Event, event_id)
    if event is None:
        raise not_found("Мероприятие не найдено")

    query = (
        _review_rows()
        .where(Review.event_id == event_id, Review.author_id == viewer.id)
        .order_by(Review.created_at, Review.id)
    )
    opens_at, closes_at = review_window(event.starts_at)
    return MyReviews(
        items=_with_authors(session, query, viewer), opens_at=opens_at, closes_at=closes_at
    )


def user_reviews(
    session: Session,
    viewer: User,
    user_id: uuid.UUID,
    kind: ReviewKind,
    limit: int,
    offset: int,
) -> ReviewPage:
    """Отзывы о пользователе одного вида; доступ — как к его профилю."""
    profile_service.get_profile_for(session, viewer, user_id)
    condition = (Review.target_id == user_id, Review.kind == kind)
    total = session.scalar(select(func.count()).select_from(Review).where(*condition))
    query = (
        _review_rows()
        .where(*condition)
        .order_by(Review.created_at.desc(), Review.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return ReviewPage(items=_with_authors(session, query, viewer), total=total or 0)
