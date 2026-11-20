from http import HTTPStatus

from django.test import Client
import pytest

from finance_planner.sessions import SessionStore

PROFILE_URL = "/api/auth/me"
# Django разбирает восьмеричную запись в куке в кавычках, поэтому \000 здесь превращается в знак NUL
NULL_CHARACTER_COOKIE = "sessionid=\"abcdefgh\\000ijklmnop\""


@pytest.mark.parametrize(
    ("session_key", "is_accepted"),
    [
        ("abcdefgh12345678", True),
        ("abcdefgh\x00ijklmnop", False),
        ("ABCDEFGH12345678", False),
        ("abc", False),
    ],
    ids=["generated-alphabet", "null-character", "uppercase", "too-short"],
)
def test_session_store_checks_key_characters(session_key: str, is_accepted: bool) -> None:
    session_store = SessionStore(session_key)

    assert (session_store.session_key == session_key) is is_accepted


@pytest.mark.django_db
def test_session_cookie_with_null_character_is_ignored(csrf_client: Client) -> None:
    response = csrf_client.get(PROFILE_URL, headers={"Cookie": NULL_CHARACTER_COOKIE})

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["code"] == "not_authenticated"
