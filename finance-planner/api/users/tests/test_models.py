from django.core.management import call_command
import pytest
from pytest_django import Settings

from users.models import User

pytestmark = pytest.mark.django_db


def test_new_user_gets_server_time_zone(settings: Settings) -> None:
    settings.TIME_ZONE = "Europe/Samara"
    user = User.objects.create_user("boris", password="lantern-orbit-58")

    assert user.time_zone == "Europe/Samara"


def test_superuser_is_created_without_email() -> None:
    call_command("createsuperuser", interactive=False, username="admin", verbosity=0)
    admin_user = User.objects.get(username="admin")

    assert admin_user.is_superuser
    assert admin_user.email == ""
