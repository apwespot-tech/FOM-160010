from collections.abc import Callable
import json

from django.http import HttpResponse
from django.test import Client
import pytest

from users.models import User

CSRF_URL = "/api/auth/csrf"
CSRF_COOKIE_NAME = "csrftoken"
CSRF_HEADER_NAME = "X-CSRFToken"
TEST_USER_PASSWORD = "quiet-river-2026"


def read_csrf_token(client: Client) -> str:
    if CSRF_COOKIE_NAME not in client.cookies:
        client.get(CSRF_URL)

    return client.cookies[CSRF_COOKIE_NAME].value


@pytest.fixture
def csrf_client() -> Client:
    # Обычный тестовый клиент Django пропускает проверку CSRF, а планеру нужно проверять её как в браузере
    return Client(enforce_csrf_checks=True)


@pytest.fixture
def csrf_token(csrf_client: Client) -> str:
    return read_csrf_token(csrf_client)


@pytest.fixture
def csrf_headers(csrf_token: str) -> dict[str, str]:
    return {CSRF_HEADER_NAME: csrf_token}


@pytest.fixture
def send_json(csrf_client: Client) -> Callable[..., HttpResponse]:
    def send(method: str, path: str, body: object | None = None, *, should_send_token: bool = True) -> HttpResponse:
        headers = {}

        if should_send_token:
            headers[CSRF_HEADER_NAME] = read_csrf_token(csrf_client)

        data = "" if body is None else json.dumps(body)

        return csrf_client.generic(method, path, data, content_type="application/json", headers=headers)

    return send


@pytest.fixture
def user_password() -> str:
    return TEST_USER_PASSWORD


@pytest.fixture
def user(db: None, user_password: str) -> User:
    return User.objects.create_user("anna", password=user_password, time_zone="Asia/Yekaterinburg")
