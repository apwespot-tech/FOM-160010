from http import HTTPStatus

from django.test import Client
import pytest

from users.models import User

pytestmark = pytest.mark.django_db


def build_change_url(user: User) -> str:
    return f"/admin/users/user/{user.id}/change/"


def build_change_form(user: User, time_zone: str) -> dict[str, str]:
    return {
        "username": user.username,
        "time_zone": time_zone,
        "is_active": "on",
        "date_joined_0": "2026-11-20",
        "date_joined_1": "10:00:00",
        "last_login_0": "",
        "last_login_1": "",
    }


@pytest.mark.parametrize("page_path", ["/admin/users/user/", "/admin/users/user/add/"], ids=["list", "add"])
def test_admin_user_pages_open(admin_client: Client, page_path: str) -> None:
    response = admin_client.get(page_path)

    assert response.status_code == HTTPStatus.OK


def test_admin_user_card_shows_time_zone(admin_client: Client, user: User) -> None:
    response = admin_client.get(build_change_url(user))
    page_text = response.content.decode()

    assert response.status_code == HTTPStatus.OK
    assert 'name="time_zone"' in page_text
    assert 'value="Asia/Yekaterinburg"' in page_text


def test_admin_saves_known_time_zone(admin_client: Client, user: User) -> None:
    response = admin_client.post(build_change_url(user), build_change_form(user, "Europe/Moscow"))
    user.refresh_from_db()

    assert response.status_code == HTTPStatus.FOUND
    assert user.time_zone == "Europe/Moscow"


def test_admin_rejects_unknown_time_zone(admin_client: Client, user: User) -> None:
    response = admin_client.post(build_change_url(user), build_change_form(user, "Mars/Olympus"))
    user.refresh_from_db()

    assert response.status_code == HTTPStatus.OK
    assert "Неизвестный часовой пояс" in response.content.decode()
    assert user.time_zone == "Asia/Yekaterinburg"
