"""Требования: проверка кода, лимит попыток, создание пользователя, роль админа."""

import threading
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User
from tests.conftest import ADMIN_PHONE, FakeClock, auth_header, get_code, login

PHONE = "+79991234567"


def request_code(client: TestClient, phone: str = PHONE) -> str:
    assert client.post("/api/auth/code", json={"phone": phone}).status_code == 200
    return get_code(client, phone)


def verify(client: TestClient, code: str, phone: str = PHONE) -> Any:
    return client.post("/api/auth/verify", json={"phone": phone, "code": code})


def wrong(code: str) -> str:
    return f"{(int(code) + 1) % 10**6:06d}"


def test_valid_code_returns_tokens(client: TestClient) -> None:
    response = verify(client, request_code(client))

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 15 * 60
    assert body["refresh_expires_in"] == 30 * 24 * 60 * 60


def test_code_cannot_be_reused(client: TestClient) -> None:
    code = request_code(client)
    assert verify(client, code).status_code == 200

    response = verify(client, code)

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_code"


def test_expired_code_rejected(client: TestClient, clock: FakeClock) -> None:
    code = request_code(client)
    clock.advance(301)
    assert verify(client, code).status_code == 400


def test_code_accepted_just_before_expiry(client: TestClient, clock: FakeClock) -> None:
    code = request_code(client)
    clock.advance(299)
    assert verify(client, code).status_code == 200


def test_code_without_request_rejected(client: TestClient) -> None:
    assert verify(client, "123456").status_code == 400


def test_fifth_wrong_attempt_invalidates_code(client: TestClient) -> None:
    code = request_code(client)
    for _ in range(5):
        assert verify(client, wrong(code)).status_code == 400

    assert verify(client, code).status_code == 400


def test_correct_code_after_four_wrong_attempts(client: TestClient) -> None:
    code = request_code(client)
    for _ in range(4):
        assert verify(client, wrong(code)).status_code == 400

    assert verify(client, code).status_code == 200


def test_concurrent_verify_of_same_code(client: TestClient, db: Session) -> None:
    code = request_code(client)
    barrier = threading.Barrier(2)
    statuses: list[int] = []

    def worker() -> None:
        barrier.wait()
        statuses.append(verify(client, code).status_code)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(statuses) == [200, 400]
    assert db.scalar(select(func.count()).select_from(User)) == 1


def test_first_login_creates_draft_user(client: TestClient, db: Session) -> None:
    tokens = verify(client, request_code(client)).json()

    profile = client.get("/api/profile", headers=auth_header(tokens)).json()
    assert profile["phone"] == PHONE
    assert profile["roles"] == ["organizer", "participant"]
    assert profile["profile_completed"] is False
    assert profile["name"] is None and profile["birth_date"] is None
    assert db.scalar(select(func.count()).select_from(User)) == 1


def test_repeat_login_reuses_user(client: TestClient, db: Session, clock: FakeClock) -> None:
    first = client.get("/api/profile", headers=auth_header(login(client, PHONE))).json()
    clock.advance(60)
    second = client.get("/api/profile", headers=auth_header(login(client, PHONE))).json()

    assert first["id"] == second["id"]
    assert db.scalar(select(func.count()).select_from(User)) == 1


def test_admin_phone_gets_admin_role(client: TestClient) -> None:
    tokens = login(client, ADMIN_PHONE)

    profile = client.get("/api/profile", headers=auth_header(tokens)).json()
    assert profile["roles"] == ["admin", "organizer", "participant"]


def test_regular_phone_has_no_admin_role(client: TestClient) -> None:
    profile = client.get("/api/profile", headers=auth_header(login(client, PHONE))).json()
    assert "admin" not in profile["roles"]
