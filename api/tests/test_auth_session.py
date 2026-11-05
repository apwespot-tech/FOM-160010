"""Требования: обновление токенов, выход, защита ручек, незаполненный профиль."""

import threading

import jwt
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.security import decode_access_token
from tests.conftest import ADMIN_PHONE, FakeClock, auth_header, login, register

PHONE = "+79991234567"


def refresh(client: TestClient, token: str) -> int:
    return client.post("/api/auth/refresh", json={"refresh_token": token}).status_code


def test_refresh_returns_new_pair(client: TestClient) -> None:
    tokens = login(client, PHONE)

    response = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 200
    new = response.json()
    assert new["refresh_token"] != tokens["refresh_token"]
    assert client.get("/api/profile", headers=auth_header(new)).status_code == 200


def test_refresh_token_cannot_be_reused(client: TestClient) -> None:
    tokens = login(client, PHONE)
    assert refresh(client, tokens["refresh_token"]) == 200
    assert refresh(client, tokens["refresh_token"]) == 401


def test_unknown_refresh_token(client: TestClient) -> None:
    assert refresh(client, "unknown-token") == 401


def test_expired_refresh_token(client: TestClient, clock: FakeClock) -> None:
    tokens = login(client, PHONE)
    clock.advance(30 * 24 * 60 * 60 + 1)
    assert refresh(client, tokens["refresh_token"]) == 401


def test_refresh_token_valid_before_expiry(client: TestClient, clock: FakeClock) -> None:
    tokens = login(client, PHONE)
    clock.advance(30 * 24 * 60 * 60 - 1)
    assert refresh(client, tokens["refresh_token"]) == 200


def test_concurrent_refresh_with_same_token(client: TestClient) -> None:
    tokens = login(client, PHONE)
    barrier = threading.Barrier(2)
    statuses: list[int] = []

    def worker() -> None:
        barrier.wait()
        statuses.append(refresh(client, tokens["refresh_token"]))

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(statuses) == [200, 401]


def test_admin_role_removed_on_refresh(app: FastAPI, client: TestClient) -> None:
    tokens = login(client, ADMIN_PHONE)
    app.state.settings.admin_phones = ""

    response = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 200
    payload = jwt.decode(response.json()["access_token"], options={"verify_signature": False})
    assert "admin" not in payload["roles"]
    profile = client.get("/api/profile", headers=auth_header(response.json())).json()
    assert "admin" not in profile["roles"]


def test_admin_role_added_on_refresh(app: FastAPI, client: TestClient) -> None:
    tokens = login(client, PHONE)
    app.state.settings.admin_phones = PHONE

    response = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    payload = decode_access_token(
        response.json()["access_token"], app.state.clock(), app.state.settings
    )
    assert "admin" in payload["roles"]


def test_logout_revokes_refresh_token(client: TestClient) -> None:
    tokens = login(client, PHONE)

    response = client.post("/api/auth/logout", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 204
    assert refresh(client, tokens["refresh_token"]) == 401


def test_repeat_logout(client: TestClient) -> None:
    tokens = login(client, PHONE)
    client.post("/api/auth/logout", json={"refresh_token": tokens["refresh_token"]})

    response = client.post("/api/auth/logout", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 204
    unknown = client.post("/api/auth/logout", json={"refresh_token": "unknown"})
    assert unknown.status_code == 204


def test_protected_endpoint_without_token(client: TestClient) -> None:
    response = client.get("/api/profile")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_token"


def test_protected_endpoint_with_garbage_token(client: TestClient) -> None:
    response = client.get("/api/profile", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401


def test_access_token_expires_after_15_minutes(client: TestClient, clock: FakeClock) -> None:
    tokens = login(client, PHONE)
    clock.advance(15 * 60 - 1)
    assert client.get("/api/profile", headers=auth_header(tokens)).status_code == 200
    clock.advance(1)
    assert client.get("/api/profile", headers=auth_header(tokens)).status_code == 401


def test_refresh_token_is_not_access_token(client: TestClient) -> None:
    tokens = login(client, PHONE)
    headers = {"Authorization": f"Bearer {tokens['refresh_token']}"}
    assert client.get("/api/profile", headers=headers).status_code == 401


def test_draft_user_blocked_from_other_endpoints(client: TestClient) -> None:
    other = register(client, "+79991234568")
    tokens = login(client, PHONE)

    response = client.get(f"/api/profile/{other['id']}", headers=auth_header(tokens))

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "profile_incomplete"


def test_draft_user_can_complete_profile(client: TestClient) -> None:
    tokens = login(client, PHONE)
    own_id = client.get("/api/profile", headers=auth_header(tokens)).json()["id"]

    response = client.patch(
        "/api/profile",
        json={"name": "Анна", "birth_date": "2000-01-15"},
        headers=auth_header(tokens),
    )

    assert response.status_code == 200
    assert response.json()["profile_completed"] is True
    # Ограничение снимается без перевыпуска токена
    assert client.get(f"/api/profile/{own_id}", headers=auth_header(tokens)).status_code == 200
