import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.deps import CompletedUser, NowDep, SessionDep
from app.models import ReviewKind
from app.schemas.review import MyReviews, ReviewCreate, ReviewOut, ReviewPage, ReviewUpdate
from app.services import review_service

router = APIRouter(tags=["reviews"])

PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@router.post("/events/{event_id}/reviews", status_code=status.HTTP_201_CREATED)
def create_review(
    event_id: uuid.UUID, body: ReviewCreate, user: CompletedUser, session: SessionDep, now: NowDep
) -> ReviewOut:
    review = review_service.create_review(session, now, user, event_id, body)
    return review_service.to_out(session, review, user)


@router.get("/events/{event_id}/reviews/mine")
def my_reviews(event_id: uuid.UUID, user: CompletedUser, session: SessionDep) -> MyReviews:
    return review_service.my_reviews(session, user, event_id)


@router.patch("/reviews/{review_id}")
def update_review(
    review_id: uuid.UUID, body: ReviewUpdate, user: CompletedUser, session: SessionDep, now: NowDep
) -> ReviewOut:
    review = review_service.update_review(session, now, user, review_id, body)
    return review_service.to_out(session, review, user)


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(
    review_id: uuid.UUID, user: CompletedUser, session: SessionDep, now: NowDep
) -> Response:
    review_service.delete_review(session, now, user, review_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/users/{user_id}/reviews")
def user_reviews(
    user_id: uuid.UUID,
    kind: ReviewKind,
    user: CompletedUser,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = PAGE_SIZE,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ReviewPage:
    return review_service.user_reviews(session, user, user_id, kind, limit, offset)
