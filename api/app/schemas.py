from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode()) > 72:
            raise ValueError("Пароль слишком длинный")
        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    event_date: datetime


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    event_date: datetime
    invite_code: str
    owner_id: int
    participants_count: int = 0


class EventDetail(EventOut):
    participants: list[UserOut] = []



class MovieCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    genre: str = Field(min_length=1, max_length=50)
    poster_url: str | None = Field(default=None, max_length=500)

    @field_validator("poster_url")
    @classmethod
    def poster_is_http(cls, value: str | None) -> str | None:
        if value and not value.startswith(("http://", "https://")):
            raise ValueError("Ссылка должна начинаться с http:// или https://")
        return value or None


class MovieOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    title: str
    genre: str
    poster_url: str | None
    added_by: int


class VoteCreate(BaseModel):
    movie_id: int


class VoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    movie_id: int
    user_id: int


class MovieResult(MovieOut):
    votes: int


class ResultsOut(BaseModel):
    total_votes: int
    my_vote_movie_id: int | None
    winner: MovieResult | None
    tie: bool
    movies: list[MovieResult]