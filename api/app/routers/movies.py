from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_member_event
from app.models import Event, Movie, User
from app.schemas import MovieCreate, MovieOut

router = APIRouter(prefix="/events/{event_id}/movies", tags=["movies"])


@router.post("", response_model=MovieOut, status_code=status.HTTP_201_CREATED)
def add_movie(
    data: MovieCreate,
    event: Event = Depends(get_member_event),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    title = data.title.strip()
    duplicate = db.scalar(
        select(Movie.id).where(
            Movie.event_id == event.id,
            func.lower(Movie.title) == title.lower(),
        )
    )
    if duplicate:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Такой фильм уже есть в этом вечере"
        )
    movie = Movie(
        event_id=event.id,
        title=title,
        genre=data.genre.strip(),
        poster_url=data.poster_url,
        added_by=current_user.id,
    )
    db.add(movie)
    db.commit()
    db.refresh(movie)
    return movie


@router.get("", response_model=list[MovieOut])
def list_movies(
    genre: str | None = Query(default=None),
    event: Event = Depends(get_member_event),
    db: Session = Depends(get_db),
):
    query = select(Movie).where(Movie.event_id == event.id).order_by(Movie.id)
    if genre:
        query = query.where(func.lower(Movie.genre) == genre.strip().lower())
    return db.scalars(query).all()


@router.delete("/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_movie(
    movie_id: int,
    event: Event = Depends(get_member_event),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    movie = db.get(Movie, movie_id)
    if movie is None or movie.event_id != event.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Фильм не найден")
    if current_user.id not in (movie.added_by, event.owner_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Удалить фильм может тот, кто его добавил, или организатор вечера",
        )
    db.delete(movie)
    db.commit()