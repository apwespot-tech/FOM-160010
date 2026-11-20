from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from users.models import get_server_time_zone, is_known_time_zone, User

USERNAME_TAKEN_MESSAGE = "Логин уже занят"
NULL_CHARACTER = "\x00"


class InvalidCredentialsError(Exception):
    pass


class UserRuleError(Exception):
    def __init__(self, field_errors: list[tuple[str, str]]) -> None:
        super().__init__(field_errors)
        self.field_errors = field_errors


def choose_time_zone(requested_time_zone: str | None) -> str:
    if requested_time_zone is not None and is_known_time_zone(requested_time_zone):
        return requested_time_zone

    return get_server_time_zone()


def register_user(username: str, password: str, requested_time_zone: str | None) -> User:
    normalized_username = User.normalize_username(username)
    field_errors = collect_registration_errors(normalized_username, password)

    if field_errors:
        raise UserRuleError(field_errors)

    time_zone = choose_time_zone(requested_time_zone)

    try:
        with transaction.atomic():
            return User.objects.create_user(normalized_username, password=password, time_zone=time_zone)
    except IntegrityError as error:
        # Логин могли занять между проверкой и записью
        raise UserRuleError([("username", USERNAME_TAKEN_MESSAGE)]) from error


def collect_registration_errors(username: str, password: str) -> list[tuple[str, str]]:
    field_errors = []

    if User.objects.filter(username=username).exists():
        field_errors.append(("username", USERNAME_TAKEN_MESSAGE))

    try:
        password_validation.validate_password(password, user=User(username=username))
    except ValidationError as error:
        # Тексты под полями формы, как и все тексты интерфейса, идут без точки в конце
        field_errors.extend(("password", message.removesuffix(".")) for message in error.messages)

    return field_errors


def check_credentials(username: str, password: str) -> User:
    normalized_username = User.normalize_username(username)

    # PostgreSQL не хранит знак NUL в тексте и ответил бы на такой запрос ошибкой, а такого логина заведомо нет
    if NULL_CHARACTER in normalized_username:
        raise InvalidCredentialsError

    user = authenticate(username=normalized_username, password=password)

    if user is None:
        raise InvalidCredentialsError

    return user


def update_profile(user: User, time_zone: str | None) -> User:
    if time_zone is not None:
        user.time_zone = time_zone
        user.save(update_fields=["time_zone"])

    return user
