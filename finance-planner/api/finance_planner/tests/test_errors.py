from collections.abc import Callable
from http import HTTPStatus
import json
import logging
from unittest import mock

from django.conf import settings
from django.core.exceptions import BadRequest, RequestDataTooBig
from django.http import Http404, HttpResponse, RawPostDataException, UnreadablePostError
from django.http.multipartparser import MultiPartParserError
from django.test import Client, RequestFactory
from ninja.errors import AuthenticationError, HttpError, Throttled
import pytest

from finance_planner import errors
from finance_planner.api import api

JsonSender = Callable[..., HttpResponse]

SAMPLE_URL = "/api/sample"
LOGIN_URL = "/api/auth/login"


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_code"),
    [
        (Http404(), HTTPStatus.NOT_FOUND, "not_found"),
        (AuthenticationError(), HTTPStatus.UNAUTHORIZED, "not_authenticated"),
        (Throttled(wait=30), HTTPStatus.TOO_MANY_REQUESTS, "too_many_requests"),
        (HttpError(403, "CSRF check Failed"), HTTPStatus.FORBIDDEN, "csrf_failed"),
        (HttpError(400, "Cannot parse request body"), HTTPStatus.BAD_REQUEST, "bad_request"),
        (RequestDataTooBig(), HTTPStatus.BAD_REQUEST, "bad_request"),
        (RawPostDataException(), HTTPStatus.BAD_REQUEST, "bad_request"),
        (MultiPartParserError(), HTTPStatus.BAD_REQUEST, "bad_request"),
        (BadRequest(), HTTPStatus.BAD_REQUEST, "bad_request"),
        (UnreadablePostError(), HTTPStatus.BAD_REQUEST, "bad_request"),
        (HttpError(418, "I'm a teapot"), HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error"),
        (RuntimeError("Сбой"), HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error"),
    ],
    ids=[
        "not-found",
        "not-authenticated",
        "throttled",
        "csrf",
        "unparsable-body",
        "body-too-big",
        "form-already-read",
        "broken-form",
        "bad-request",
        "unreadable-body",
        "unknown-http-error",
        "unexpected-error",
    ],
)
def test_error_has_code_and_russian_text(error: Exception, expected_status: HTTPStatus, expected_code: str) -> None:
    request = RequestFactory().get(SAMPLE_URL)

    with mock.patch.object(errors.logger, "error"):
        response = api.on_exception(request, error)

    body = json.loads(response.content)

    assert response.status_code == expected_status
    assert body == {"code": expected_code, "detail": errors.ERROR_DETAILS[expected_code]}


def test_unexpected_error_is_logged_with_traceback() -> None:
    request = RequestFactory().get(SAMPLE_URL)
    error = RuntimeError("Сбой")

    with mock.patch.object(errors.logger, "error") as log_error:
        api.on_exception(request, error)

    assert log_error.call_args.kwargs["exc_info"] is error


def test_suspicious_operation_is_logged_as_security_error() -> None:
    request = RequestFactory().get(SAMPLE_URL)
    error = RequestDataTooBig("Тело больше допустимого")
    security_logger = logging.getLogger("django.security.RequestDataTooBig")

    with mock.patch.object(security_logger, "error") as log_error:
        response = api.on_exception(request, error)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert log_error.call_args.kwargs["exc_info"] is error


@pytest.mark.django_db
def test_failing_route_answers_with_json(send_json: JsonSender) -> None:
    body = {"username": "boris", "password": "lantern-orbit-58"}

    with mock.patch("users.services.register_user", side_effect=RuntimeError("Сбой")), mock.patch.object(errors.logger, "error"):
        response = send_json("POST", "/api/auth/register", body)

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json() == {"code": "internal_error", "detail": "Внутренняя ошибка сервера"}


@pytest.mark.django_db
def test_oversized_body_returns_bad_request(send_json: JsonSender) -> None:
    oversized_username = "a" * (settings.DATA_UPLOAD_MAX_MEMORY_SIZE + 1)
    response = send_json("POST", LOGIN_URL, {"username": oversized_username, "password": "x"})

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()["code"] == "bad_request"


@pytest.mark.django_db
def test_form_body_returns_bad_request(csrf_client: Client, csrf_token: str) -> None:
    # Для POST проверка CSRF сначала ищет токен в полях формы и сама читает тело формы, заголовок этого не отменяет.
    # После этого Ninja тело уже не получит
    form_data = {"csrfmiddlewaretoken": csrf_token, "username": "anna", "password": "x"}
    response = csrf_client.post(LOGIN_URL, form_data)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()["code"] == "bad_request"


@pytest.mark.django_db
@pytest.mark.usefixtures("csrf_token")
def test_form_without_boundary_returns_bad_request(csrf_client: Client) -> None:
    # Для POST проверка CSRF сначала сама разбирает форму, поэтому испорченная форма падает раньше сверки токенов
    response = csrf_client.generic("POST", LOGIN_URL, b"username=anna", content_type="multipart/form-data")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()["code"] == "bad_request"
