import functools
import zoneinfo

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

TIME_ZONE_MAX_LENGTH = 64
UNKNOWN_TIME_ZONE_MESSAGE = "Неизвестный часовой пояс"
# localtime в образе Python ссылается на пояс самого контейнера, а Factory в базе IANA значит «пояс не задан»
EXCLUDED_TIME_ZONE_NAMES = frozenset({"localtime", "Factory"})


@functools.cache
def get_known_time_zones() -> frozenset[str]:
    return frozenset(zoneinfo.available_timezones() - EXCLUDED_TIME_ZONE_NAMES)


def is_known_time_zone(name: str) -> bool:
    return name in get_known_time_zones()


def validate_time_zone(name: str) -> None:
    if not is_known_time_zone(name):
        raise ValidationError(UNKNOWN_TIME_ZONE_MESSAGE, code="unknown_time_zone")


def get_server_time_zone() -> str:
    return settings.TIME_ZONE


class User(AbstractUser):
    # Почта при регистрации не собирается, поэтому createsuperuser её не спрашивает
    REQUIRED_FIELDS = []

    # Функция вместо значения: иначе пояс сервера попал бы в миграцию и зависел от DJANGO_TIME_ZONE при её создании.
    # Валидатор нужен админке: пояс в обход API должен проходить ту же проверку
    time_zone = models.CharField("часовой пояс", max_length=TIME_ZONE_MAX_LENGTH, default=get_server_time_zone, validators=[validate_time_zone])
