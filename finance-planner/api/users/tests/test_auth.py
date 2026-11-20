from collections.abc import Callable
from http import HTTPStatus
from unittest import mock

from django.contrib.sessions.models import Session
from django.http import HttpResponse
from django.test import Client
import pytest
from pytest_django import Settings

from users.models import User

pytestmark = pytest.mark.django_db

JsonSender = Callable[..., HttpResponse]

CSRF_URL = "/api/auth/csrf"
REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"
LOGOUT_URL = "/api/auth/logout"
PROFILE_URL = "/api/auth/me"
STRONG_PASSWORD = "lantern-orbit-58"
SHORTEST_PASSWORD = "zq7#mPx2"
LONGEST_PASSWORD = "orbit-" * 21 + "xy"
FALLBACK_TIME_ZONE = "Europe/Samara"


def read_errors(response: HttpResponse) -> list[tuple[str, str]]:
    detail = response.json()["detail"]

    return [(error["loc"][-1], error["type"]) for error in detail]


def test_csrf_route_sets_token_cookie(csrf_client: Client) -> None:
    response = csrf_client.get(CSRF_URL)

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b""
    assert "csrftoken" in response.cookies


def test_register_creates_user_and_starts_session(send_json: JsonSender) -> None:
    body = {"username": "boris", "password": STRONG_PASSWORD, "time_zone": "Europe/Moscow"}
    response = send_json("POST", REGISTER_URL, body)
    profile_response = send_json("GET", PROFILE_URL)
    created_user = User.objects.get(username="boris")

    assert response.status_code == HTTPStatus.CREATED
    assert response.json() == {"id": created_user.id, "username": "boris", "time_zone": "Europe/Moscow"}
    assert created_user.check_password(STRONG_PASSWORD)
    assert profile_response.status_code == HTTPStatus.OK
    assert profile_response.json()["username"] == "boris"


def test_register_without_time_zone_uses_server_zone(send_json: JsonSender, settings: Settings) -> None:
    settings.TIME_ZONE = FALLBACK_TIME_ZONE
    response = send_json("POST", REGISTER_URL, {"username": "boris", "password": STRONG_PASSWORD})

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["time_zone"] == FALLBACK_TIME_ZONE


@pytest.mark.parametrize("requested_time_zone", [None, "Mars/Olympus", "localtime", "Factory", "   "])
def test_register_replaces_unknown_time_zone(send_json: JsonSender, settings: Settings, requested_time_zone: str | None) -> None:
    settings.TIME_ZONE = FALLBACK_TIME_ZONE
    body = {"username": "boris", "password": STRONG_PASSWORD, "time_zone": requested_time_zone}
    response = send_json("POST", REGISTER_URL, body)

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["time_zone"] == FALLBACK_TIME_ZONE


def test_register_keeps_legacy_time_zone_name(send_json: JsonSender) -> None:
    # Браузеры до сих пор отдают и устаревшие имена поясов, их знает пакет tzdata
    body = {"username": "boris", "password": STRONG_PASSWORD, "time_zone": "Europe/Kiev"}
    response = send_json("POST", REGISTER_URL, body)

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["time_zone"] == "Europe/Kiev"


@pytest.mark.parametrize(
    ("requested_username", "stored_username"),
    [
        ("  boris  ", "boris"),
        ("анна", "анна"),
        ("\ufb01ona", "fiona"),
        ("bor", "bor"),
        ("b" * 150, "b" * 150),
    ],
    ids=["spaces", "cyrillic", "nfkc-ligature", "shortest", "longest"],
)
def test_register_normalizes_username(send_json: JsonSender, requested_username: str, stored_username: str) -> None:
    response = send_json("POST", REGISTER_URL, {"username": requested_username, "password": STRONG_PASSWORD})

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["username"] == stored_username
    assert User.objects.filter(username=stored_username).exists()


@pytest.mark.parametrize("password", [SHORTEST_PASSWORD, LONGEST_PASSWORD], ids=["shortest", "longest"])
def test_register_accepts_password_length_limits(send_json: JsonSender, password: str) -> None:
    response = send_json("POST", REGISTER_URL, {"username": "boris", "password": password})

    assert response.status_code == HTTPStatus.CREATED


def test_register_rejects_taken_username(send_json: JsonSender, user: User) -> None:
    response = send_json("POST", REGISTER_URL, {"username": user.username, "password": STRONG_PASSWORD})
    expected_error = {"type": "planner_rule", "loc": ["body", "payload", "username"], "msg": "Логин уже занят"}

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert response.json() == {"code": "validation_error", "detail": [expected_error]}


def test_register_reports_username_taken_during_registration(send_json: JsonSender, user: User) -> None:
    # Предварительная проверка не видит логин, занятый параллельным запросом, его ловит уникальность в базе
    with mock.patch("users.services.collect_registration_errors", return_value=[]):
        response = send_json("POST", REGISTER_URL, {"username": user.username, "password": STRONG_PASSWORD})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_errors(response) == [("username", "planner_rule")]


@pytest.mark.parametrize("weak_password", ["12345678", "qwertyuiop", "boris-smirnov"], ids=["numeric", "common", "like-username"])
def test_register_rejects_weak_password(send_json: JsonSender, weak_password: str) -> None:
    response = send_json("POST", REGISTER_URL, {"username": "boris-smirnov", "password": weak_password})
    errors = response.json()["detail"]

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert errors
    assert all(error["loc"] == ["body", "payload", "password"] for error in errors)
    assert all(error["type"] == "planner_rule" for error in errors)
    assert not any(error["msg"].endswith(".") for error in errors)
    assert not User.objects.filter(username="boris-smirnov").exists()


@pytest.mark.parametrize(
    ("body", "expected_error"),
    [
        ({"username": "bo", "password": STRONG_PASSWORD}, ("username", "string_too_short")),
        ({"username": "b" * 151, "password": STRONG_PASSWORD}, ("username", "string_too_long")),
        ({"username": "\ufdfa" * 9, "password": STRONG_PASSWORD}, ("username", "string_too_long")),
        ({"username": "boris smirnov", "password": STRONG_PASSWORD}, ("username", "planner_format")),
        ({"username": "boris\u037a", "password": STRONG_PASSWORD}, ("username", "planner_format")),
        ({"username": "anna\u200d", "password": STRONG_PASSWORD}, ("username", "planner_format")),
        ({"username": "x\u0301yz", "password": STRONG_PASSWORD}, ("username", "planner_format")),
        ({"username": "an\x00na", "password": STRONG_PASSWORD}, ("username", "planner_format")),
        ({"username": 42, "password": STRONG_PASSWORD}, ("username", "string_type")),
        ({"password": STRONG_PASSWORD}, ("username", "missing")),
        ({"username": "boris", "password": "short"}, ("password", "string_too_short")),
        ({"username": "boris", "password": LONGEST_PASSWORD + "z"}, ("password", "string_too_long")),
        ({"username": "boris", "password": STRONG_PASSWORD, "email": "boris@example.com"}, ("email", "extra_forbidden")),
    ],
    ids=[
        "username-short",
        "username-long",
        "username-long-after-nfkc",
        "username-space",
        "username-space-after-nfkc",
        "username-zero-width-joiner",
        "username-combining-mark",
        "username-null-character",
        "username-number",
        "username-missing",
        "password-short",
        "password-long",
        "extra-field",
    ],
)
def test_register_rejects_malformed_body(send_json: JsonSender, body: dict[str, object], expected_error: tuple[str, str]) -> None:
    response = send_json("POST", REGISTER_URL, body)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert response.json()["code"] == "validation_error"
    assert read_errors(response) == [expected_error]


def test_register_replaces_existing_session(send_json: JsonSender, csrf_client: Client, user: User) -> None:
    csrf_client.force_login(user)
    response = send_json("POST", REGISTER_URL, {"username": "boris", "password": STRONG_PASSWORD})
    profile_response = send_json("GET", PROFILE_URL)

    assert response.status_code == HTTPStatus.CREATED
    assert profile_response.json()["username"] == "boris"


@pytest.mark.usefixtures("csrf_token")
@pytest.mark.parametrize("path", [REGISTER_URL, LOGIN_URL])
def test_register_and_login_require_csrf_token(send_json: JsonSender, path: str) -> None:
    response = send_json("POST", path, {"username": "boris", "password": STRONG_PASSWORD}, should_send_token=False)

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json() == {"code": "csrf_failed", "detail": "Нет токена CSRF или он устарел"}


@pytest.mark.usefixtures("csrf_token")
def test_csrf_token_is_checked_before_body(send_json: JsonSender) -> None:
    response = send_json("POST", REGISTER_URL, {"unexpected": True}, should_send_token=False)

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_unparsable_body_returns_bad_request(csrf_client: Client, csrf_headers: dict[str, str]) -> None:
    response = csrf_client.generic("POST", LOGIN_URL, "{oops", content_type="application/json", headers=csrf_headers)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {"code": "bad_request", "detail": "Тело запроса не разбирается как JSON"}


def test_login_starts_session(send_json: JsonSender, user: User, user_password: str) -> None:
    response = send_json("POST", LOGIN_URL, {"username": "anna", "password": user_password})
    profile_response = send_json("GET", PROFILE_URL)

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"id": user.id, "username": "anna", "time_zone": "Asia/Yekaterinburg"}
    assert profile_response.status_code == HTTPStatus.OK


@pytest.mark.parametrize("username", ["anna", "nobody", "an\x00na"], ids=["wrong-password", "unknown-user", "null-character"])
def test_login_rejects_wrong_credentials(send_json: JsonSender, user: User, username: str) -> None:
    response = send_json("POST", LOGIN_URL, {"username": username, "password": "wrong-password"})

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json() == {"code": "invalid_credentials", "detail": "Неверный логин или пароль"}


def test_login_is_case_sensitive(send_json: JsonSender, user: User, user_password: str) -> None:
    response = send_json("POST", LOGIN_URL, {"username": "ANNA", "password": user_password})

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["code"] == "invalid_credentials"


def test_login_rejects_inactive_user(send_json: JsonSender, user: User, user_password: str) -> None:
    user.is_active = False
    user.save(update_fields=["is_active"])
    response = send_json("POST", LOGIN_URL, {"username": "anna", "password": user_password})

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["code"] == "invalid_credentials"


def test_login_rejects_empty_password(send_json: JsonSender, user: User) -> None:
    response = send_json("POST", LOGIN_URL, {"username": "anna", "password": ""})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_errors(response) == [("password", "string_too_short")]


def test_login_replaces_session(send_json: JsonSender, csrf_client: Client, user: User, user_password: str) -> None:
    other_user = User.objects.create_user("boris", password=STRONG_PASSWORD)
    csrf_client.force_login(other_user)
    old_session_key = csrf_client.session.session_key
    response = send_json("POST", LOGIN_URL, {"username": "anna", "password": user_password})
    profile_response = send_json("GET", PROFILE_URL)

    assert response.status_code == HTTPStatus.OK
    assert profile_response.json()["username"] == "anna"
    assert csrf_client.session.session_key != old_session_key
    assert not Session.objects.filter(session_key=old_session_key).exists()


def test_login_changes_csrf_token(
    send_json: JsonSender,
    csrf_client: Client,
    csrf_headers: dict[str, str],
    user: User,
    user_password: str,
) -> None:
    send_json("POST", LOGIN_URL, {"username": "anna", "password": user_password})
    stale_token_response = csrf_client.generic("PATCH", PROFILE_URL, "{}", content_type="application/json", headers=csrf_headers)
    fresh_token_response = send_json("PATCH", PROFILE_URL, {})

    assert stale_token_response.status_code == HTTPStatus.FORBIDDEN
    assert stale_token_response.json()["code"] == "csrf_failed"
    assert fresh_token_response.status_code == HTTPStatus.OK


def test_logout_ends_session(send_json: JsonSender, csrf_client: Client, user: User) -> None:
    csrf_client.force_login(user)
    session_key = csrf_client.session.session_key
    response = send_json("POST", LOGOUT_URL)
    profile_response = send_json("GET", PROFILE_URL)

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b""
    assert not Session.objects.filter(session_key=session_key).exists()
    assert profile_response.status_code == HTTPStatus.UNAUTHORIZED
    assert profile_response.json() == {"code": "not_authenticated", "detail": "Требуется вход"}


def test_profile_requires_session(send_json: JsonSender) -> None:
    response = send_json("GET", PROFILE_URL)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["code"] == "not_authenticated"


def test_profile_update_changes_time_zone(send_json: JsonSender, csrf_client: Client, user: User) -> None:
    csrf_client.force_login(user)
    response = send_json("PATCH", PROFILE_URL, {"time_zone": " Europe/Moscow "})
    user.refresh_from_db()

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"id": user.id, "username": "anna", "time_zone": "Europe/Moscow"}
    assert user.time_zone == "Europe/Moscow"


def test_profile_update_with_empty_body_changes_nothing(send_json: JsonSender, csrf_client: Client, user: User) -> None:
    csrf_client.force_login(user)
    response = send_json("PATCH", PROFILE_URL, {})
    user.refresh_from_db()

    assert response.status_code == HTTPStatus.OK
    assert user.time_zone == "Asia/Yekaterinburg"


@pytest.mark.parametrize(
    ("body", "expected_error"),
    [
        ({"time_zone": "Mars/Olympus"}, ("time_zone", "planner_rule")),
        ({"time_zone": "localtime"}, ("time_zone", "planner_rule")),
        ({"time_zone": "Europe/Mos\x00cow"}, ("time_zone", "planner_rule")),
        ({"time_zone": None}, ("time_zone", "string_type")),
        ({"username": "boris"}, ("username", "extra_forbidden")),
    ],
    ids=["unknown-zone", "container-zone-link", "null-character", "null", "extra-field"],
)
def test_profile_update_rejects_bad_body(
    send_json: JsonSender,
    csrf_client: Client,
    user: User,
    body: dict[str, object],
    expected_error: tuple[str, str],
) -> None:
    csrf_client.force_login(user)
    response = send_json("PATCH", PROFILE_URL, body)
    user.refresh_from_db()

    assert response.status_code == HTTPStatus.UNPROCESSABLE_CONTENT
    assert read_errors(response) == [expected_error]
    assert user.time_zone == "Asia/Yekaterinburg"
