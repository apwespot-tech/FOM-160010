from typing import Annotated

from django.core.exceptions import ValidationError
from ninja import Schema
from pydantic import AfterValidator, BeforeValidator, ConfigDict, StringConstraints
from pydantic_core import PydanticCustomError

from users.models import is_known_time_zone, UNKNOWN_TIME_ZONE_MESSAGE, User

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 150
USERNAME_CHARACTERS_MESSAGE = "Логин может состоять только из букв, цифр и знаков @ . + - _"
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


def check_username_characters(username: str) -> str:
    # Валидатор самой модели, а не pattern Pydantic: в движке регулярных выражений Pydantic знак \w шире, чем в Python
    try:
        User.username_validator(username)
    except ValidationError as error:
        raise PydanticCustomError("planner_format", USERNAME_CHARACTERS_MESSAGE) from error

    return username


def check_known_time_zone(time_zone: str) -> str:
    if not is_known_time_zone(time_zone):
        raise PydanticCustomError("planner_rule", UNKNOWN_TIME_ZONE_MESSAGE)

    return time_zone


NEW_USERNAME_CONSTRAINTS = StringConstraints(strip_whitespace=True, min_length=USERNAME_MIN_LENGTH, max_length=USERNAME_MAX_LENGTH)

# Длина и знаки проверяются после нормализации NFKC, как в формах Django: она может удлинить логин и добавить в него пробел.
# BeforeValidator стоит после ограничений длины, поэтому оборачивает их и выполняется раньше, а ошибки длины остаются string_too_*
NewUsername = Annotated[str, NEW_USERNAME_CONSTRAINTS, BeforeValidator(User.normalize_username), AfterValidator(check_username_characters)]
NewPassword = Annotated[str, StringConstraints(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)]
LoginUsername = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
LoginPassword = Annotated[str, StringConstraints(min_length=1)]
RequestedTimeZone = Annotated[str, StringConstraints(strip_whitespace=True)]
KnownTimeZone = Annotated[str, StringConstraints(strip_whitespace=True), AfterValidator(check_known_time_zone)]


class StrictInput(Schema):
    model_config = ConfigDict(extra="forbid")


class RegisterInput(StrictInput):
    username: NewUsername
    password: NewPassword
    time_zone: RequestedTimeZone | None = None


class LoginInput(StrictInput):
    username: LoginUsername
    password: LoginPassword


class ProfileUpdateInput(StrictInput):
    # None значит, что поле не прислали. Тип без None нарочно: явный null не пройдёт проверку строки, а OpenAPI не покажет его допустимым
    time_zone: KnownTimeZone = None


class UserOut(Schema):
    id: int
    username: str
    time_zone: str
