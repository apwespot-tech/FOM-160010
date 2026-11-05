"""Требования: запрос кода, ограничение частоты, тестовая ручка."""

import threading

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuthCode
from tests.conftest import FakeClock, get_code

PHONE = "+79991234567"


def test_request_code_normalizes_phone_and_stores_code(client: TestClient, db: Session) -> None:
    response = client.post("/api/auth/code", json={"phone": "8 (999) 123-45-67"})

    assert response.status_code == 200
    assert response.json() == {"expires_in": 300}
    assert "code" not in response.json()
    codes = db.scalars(select(AuthCode).where(AuthCode.phone == PHONE)).all()
    assert len(codes) == 1
    assert len(codes[0].code) == 6 and codes[0].code.isdigit()


def test_request_code_invalid_phone(client: TestClient, db: Session) -> None:
    response = client.post("/api/auth/code", json={"phone": "12ab"})

    assert response.status_code == 422
    assert db.scalars(select(AuthCode)).all() == []


def test_new_code_revokes_previous(client: TestClient, clock: FakeClock) -> None:
    client.post("/api/auth/code", json={"phone": PHONE})
    old_code = get_code(client, PHONE)
    clock.advance(60)

    assert client.post("/api/auth/code", json={"phone": PHONE}).status_code == 200
    new_code = get_code(client, PHONE)

    if old_code != new_code:
        response = client.post("/api/auth/verify", json={"phone": PHONE, "code": old_code})
        assert response.status_code == 400
    response = client.post("/api/auth/verify", json={"phone": PHONE, "code": new_code})
    assert response.status_code == 200


def test_old_code_rejected_after_new_one(client: TestClient, db: Session, clock: FakeClock) -> None:
    client.post("/api/auth/code", json={"phone": PHONE})
    clock.advance(60)
    client.post("/api/auth/code", json={"phone": PHONE})

    codes = db.scalars(select(AuthCode).order_by(AuthCode.created_at)).all()
    assert codes[0].revoked_at is not None
    assert codes[1].revoked_at is None


def test_repeat_request_within_cooldown(client: TestClient, clock: FakeClock) -> None:
    client.post("/api/auth/code", json={"phone": PHONE})
    code = get_code(client, PHONE)
    clock.advance(30)

    response = client.post("/api/auth/code", json={"phone": PHONE})

    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "code_cooldown"
    assert response.json()["detail"]["retry_after"] == 30
    assert response.headers["Retry-After"] == "30"
    assert get_code(client, PHONE) == code


def test_repeat_request_exactly_after_cooldown(client: TestClient, clock: FakeClock) -> None:
    client.post("/api/auth/code", json={"phone": PHONE})
    clock.advance(60)

    assert client.post("/api/auth/code", json={"phone": PHONE}).status_code == 200


def verify(client: TestClient, code: str) -> int:
    return client.post("/api/auth/verify", json={"phone": PHONE, "code": code}).status_code


def test_verified_code_does_not_block_new_request(client: TestClient, clock: FakeClock) -> None:
    client.post("/api/auth/code", json={"phone": PHONE})
    first = get_code(client, PHONE)
    assert verify(client, first) == 200
    clock.advance(20)

    response = client.post("/api/auth/code", json={"phone": PHONE})

    assert response.status_code == 200
    second = get_code(client, PHONE)
    assert verify(client, second) == 200


def test_exhausted_code_still_blocks(client: TestClient, clock: FakeClock) -> None:
    client.post("/api/auth/code", json={"phone": PHONE})
    wrong = "000000" if get_code(client, PHONE) != "000000" else "111111"
    for _ in range(5):
        assert verify(client, wrong) == 400
    clock.advance(30)

    response = client.post("/api/auth/code", json={"phone": PHONE})

    assert response.status_code == 429
    assert response.json()["detail"]["retry_after"] == 30


def test_concurrent_requests_after_login(client: TestClient, clock: FakeClock) -> None:
    client.post("/api/auth/code", json={"phone": PHONE})
    assert verify(client, get_code(client, PHONE)) == 200
    clock.advance(5)
    barrier = threading.Barrier(2)
    statuses: list[int] = []

    def worker() -> None:
        barrier.wait()
        statuses.append(client.post("/api/auth/code", json={"phone": PHONE}).status_code)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(statuses) == [200, 429]


def test_cooldown_is_per_phone(client: TestClient) -> None:
    assert client.post("/api/auth/code", json={"phone": PHONE}).status_code == 200
    assert client.post("/api/auth/code", json={"phone": "+79991234568"}).status_code == 200


def test_test_code_returns_active_code(client: TestClient, db: Session) -> None:
    client.post("/api/auth/code", json={"phone": PHONE})
    stored = db.scalars(select(AuthCode)).one().code

    response = client.get("/api/auth/test/code", params={"phone": "8 999 123 45 67"})

    assert response.status_code == 200
    assert response.json() == {"code": stored}


def test_test_code_not_requested(client: TestClient) -> None:
    assert client.get("/api/auth/test/code", params={"phone": PHONE}).status_code == 404


def test_test_code_expired(client: TestClient, clock: FakeClock) -> None:
    client.post("/api/auth/code", json={"phone": PHONE})
    clock.advance(301)
    assert client.get("/api/auth/test/code", params={"phone": PHONE}).status_code == 404


def test_test_code_used(client: TestClient) -> None:
    client.post("/api/auth/code", json={"phone": PHONE})
    client.post("/api/auth/verify", json={"phone": PHONE, "code": get_code(client, PHONE)})
    assert client.get("/api/auth/test/code", params={"phone": PHONE}).status_code == 404


def test_test_code_disabled(app: FastAPI, client: TestClient, db: Session) -> None:
    client.post("/api/auth/code", json={"phone": PHONE})
    stored = db.scalars(select(AuthCode)).one().code
    app.state.settings.auth_test_endpoints = False

    response = client.get("/api/auth/test/code", params={"phone": PHONE})

    assert response.status_code == 404
    assert stored not in response.text
