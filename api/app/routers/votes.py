from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_member_event
from app.models import Event, Movie, User, Vote
from app.schemas import MovieOut, MovieResult, ResultsOut, VoteCreate, VoteOut

router = APIRouter(prefix="/events/{event_id}", tags=["votes"])

ALREADY_VOTED = "Вы уже проголосовали в этом вечере"


@router.post("/votes", response_model=VoteOut, status_code=status.HTTP_201_CREATED)
def cast_vote(
    data: VoteCreate,
    event: Event = Depends(get_member_event),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    movie = db.get(Movie, data.movie_id)
    if movie is None or movie.event_id != event.id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Фильм не найден в этом вечере"
        )

    already_voted = db.scalar(
        select(Vote.id).where(
            Vote.event_id == event.id, Vote.user_id == current_user.id
        )
    )
    if already_voted:
        raise HTTPException(status.HTTP_409_CONFLICT, ALREADY_VOTED)

    vote = Vote(event_id=event.id, user_id=current_user.id, movie_id=movie.id)
    db.add(vote)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, ALREADY_VOTED)
    db.refresh(vote)
    return vote


@router.get("/results", response_model=ResultsOut)
def get_results(
    event: Event = Depends(get_member_event),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    counts = (
        select(Vote.movie_id, func.count().label("cnt"))
        .where(Vote.event_id == event.id)
        .group_by(Vote.movie_id)
        .subquery()
    )
    votes_expr = func.coalesce(counts.c.cnt, 0)
    rows = db.execute(
        select(Movie, votes_expr)
        .outerjoin(counts, counts.c.movie_id == Movie.id)
        .where(Movie.event_id == event.id)
        .order_by(votes_expr.desc(), Movie.id)
    ).all()

    movies = [
        MovieResult(**MovieOut.model_validate(movie).model_dump(), votes=cnt)
        for movie, cnt in rows
    ]
    top_votes = movies[0].votes if movies else 0
    leaders = [m for m in movies if m.votes == top_votes] if top_votes > 0 else []

    my_vote = db.scalar(
        select(Vote.movie_id).where(
            Vote.event_id == event.id, Vote.user_id == current_user.id
        )
    )
    return ResultsOut(
        total_votes=sum(m.votes for m in movies),
        my_vote_movie_id=my_vote,
        winner=leaders[0] if len(leaders) == 1 else None,
        tie=len(leaders) > 1,
        movies=movies,
    )