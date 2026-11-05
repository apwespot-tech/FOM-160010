"""Требования профиля: представление, заполненность, валидация, уникальность, доступ."""

import threading
import uuid
from datetime import date
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import User
from tests.conftest import ADMIN_PHONE, FakeClock, auth_header, get_code, login, register

PHONE = "+79991234567"
OTHER_PHONE = "+79991234568"


def patch_own(client: TestClient, tokens: dict[str, Any], payload: dict[str, Any]) -> Any:
    return client.patch("/api/profile", json=payload, headers=auth_header(tokens))


# --- свой профиль ---


def test_get_own_profile(client: TestClient) -> None:
    user = register(client, PHONE, name="Анна", birth_date="2000-11-01")

    response = client.get("/api/profile", headers=auth_header(user))

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "id": user["id"],
        "phone": PHONE,
        "name": "Анна",
        "birth_date": "2000-11-01",
        "age": 25,
        "email": None,
        "telegram": None,
        "about": None,
        "city": None,
        "interests": [],
        "avatar_id": None,
        "cover_id": None,
        "created_at": body["created_at"],
        "stats": {"organized_count": 0, "attended_count": 0},
        "ratings": {
            "as_organizer": {"average": None, "count": 0},
            "as_participant": {"average": None, "count": 0},
        },
        "roles": ["organizer", "participant"],
        "profile_completed": True,
    }
    assert body["created_at"]


def test_age_on_birthday(client: TestClient) -> None:
    user = register(client, PHONE, birth_date="2000-10-31")
    assert client.get("/api/profile", headers=auth_header(user)).json()["age"] == 26


def test_partial_update_and_clear_optional(client: TestClient) -> None:
    user = register(client, PHONE)
    response = patch_own(
        client,
        user,
        {"telegram": "@anna_k", "email": "ann@example.com"},
    )
    assert response.status_code == 200
    assert response.json()["telegram"] == "@anna_k"
    assert response.json()["name"] == "Анна"

    response = patch_own(client, user, {"telegram": None})

    assert response.status_code == 200
    assert response.json()["telegram"] is None
    assert response.json()["email"] == "ann@example.com"


def test_cannot_clear_name(client: TestClient) -> None:
    user = register(client, PHONE)
    assert patch_own(client, user, {"name": None}).status_code == 422


def test_cannot_change_own_phone_or_roles(client: TestClient) -> None:
    user = register(client, PHONE)

    assert patch_own(client, user, {"phone": OTHER_PHONE}).status_code == 422
    assert patch_own(client, user, {"roles": ["admin"]}).status_code == 422
    profile = client.get("/api/profile", headers=auth_header(user)).json()
    assert profile["phone"] == PHONE
    assert "admin" not in profile["roles"]


def test_birth_date_in_future_rejected(client: TestClient) -> None:
    user = register(client, PHONE)

    response = patch_own(client, user, {"birth_date": "2026-11-01"})

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_birth_date"
    assert client.get("/api/profile", headers=auth_header(user)).json()["birth_date"] == (
        "2000-01-15"
    )


def test_birth_date_today_rejected(client: TestClient) -> None:
    user = register(client, PHONE)
    response = patch_own(client, user, {"birth_date": "2026-10-31"})
    assert response.status_code == 422
    assert response.json()["detail"]["message"] == "Сервисом можно пользоваться с 14 лет"


def test_minimum_age_boundary(client: TestClient) -> None:
    # Сегодня (START) — 2026-10-31
    user = register(client, PHONE)

    younger = patch_own(client, user, {"birth_date": "2012-11-01"})
    exactly = patch_own(client, user, {"birth_date": "2012-10-31"})

    assert younger.status_code == 422
    assert younger.json()["detail"]["code"] == "invalid_birth_date"
    assert younger.json()["detail"]["message"] == "Сервисом можно пользоваться с 14 лет"
    assert exactly.status_code == 200
    assert exactly.json()["age"] == 14


def test_saved_underage_profile_stays_editable(client: TestClient, db: Session) -> None:
    user = register(client, PHONE)
    db.execute(
        update(User).where(User.id == uuid.UUID(user["id"])).values(birth_date=date(2020, 1, 1))
    )
    db.commit()

    response = patch_own(client, user, {"about": "Люблю настолки"})

    assert response.status_code == 200
    assert response.json()["birth_date"] == "2020-01-01"
    assert response.json()["profile_completed"] is True


def test_birth_date_lower_bound(client: TestClient) -> None:
    user = register(client, PHONE)
    assert patch_own(client, user, {"birth_date": "1900-01-01"}).status_code == 200
    assert patch_own(client, user, {"birth_date": "1899-12-31"}).status_code == 422


def test_blank_name_and_bad_telegram_rejected(client: TestClient) -> None:
    user = register(client, PHONE)
    assert patch_own(client, user, {"name": "   "}).status_code == 422
    assert patch_own(client, user, {"telegram": "@abc"}).status_code == 422


def test_profile_completed_requires_both_fields(client: TestClient) -> None:
    tokens = login(client, PHONE)
    assert patch_own(client, tokens, {"name": "Анна"}).json()["profile_completed"] is False
    response = patch_own(client, tokens, {"birth_date": "2000-01-15"})
    assert response.json()["profile_completed"] is True


# --- уникальность email ---


def test_email_taken_case_insensitive(client: TestClient) -> None:
    first = register(client, PHONE)
    second = register(client, OTHER_PHONE)
    assert patch_own(client, first, {"email": "ann@example.com"}).status_code == 200

    response = patch_own(client, second, {"email": "Ann@Example.com"})

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "email_taken"


def test_own_email_can_be_resaved(client: TestClient) -> None:
    user = register(client, PHONE)
    assert patch_own(client, user, {"email": "ann@example.com"}).status_code == 200
    assert patch_own(client, user, {"email": "ann@example.com"}).status_code == 200


def test_concurrent_same_email(client: TestClient) -> None:
    users = [register(client, PHONE), register(client, OTHER_PHONE)]
    barrier = threading.Barrier(2)
    statuses: list[int] = []

    def worker(tokens: dict[str, Any]) -> None:
        barrier.wait()
        statuses.append(patch_own(client, tokens, {"email": "same@example.com"}).status_code)

    threads = [threading.Thread(target=worker, args=(user,)) for user in users]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(statuses) == [200, 409]


# --- чужой профиль ---


def test_own_id_via_profile_by_id(client: TestClient) -> None:
    user = register(client, PHONE)
    response = client.get(f"/api/profile/{user['id']}", headers=auth_header(user))
    assert response.status_code == 200
    assert response.json()["phone"] == PHONE


def test_admin_views_other_profile(client: TestClient) -> None:
    user = register(client, PHONE)
    admin = register(client, ADMIN_PHONE)

    response = client.get(f"/api/profile/{user['id']}", headers=auth_header(admin))

    assert response.status_code == 200
    assert response.json()["phone"] == PHONE


def test_admin_views_missing_profile(client: TestClient) -> None:
    admin = register(client, ADMIN_PHONE)
    response = client.get(f"/api/profile/{uuid.uuid4()}", headers=auth_header(admin))
    assert response.status_code == 404


def test_regular_user_cannot_view_other_profile(client: TestClient) -> None:
    user = register(client, PHONE)
    other = register(client, OTHER_PHONE)

    response = client.get(f"/api/profile/{other['id']}", headers=auth_header(user))

    assert response.status_code == 403
    assert OTHER_PHONE not in response.text


def test_regular_user_gets_403_for_missing_profile(client: TestClient) -> None:
    user = register(client, PHONE)
    response = client.get(f"/api/profile/{uuid.uuid4()}", headers=auth_header(user))
    assert response.status_code == 403


# --- изменение чужого профиля администратором ---


def patch_other(client: TestClient, tokens: dict[str, Any], user_id: str, payload: Any) -> Any:
    return client.patch(f"/api/profile/{user_id}", json=payload, headers=auth_header(tokens))


def test_admin_updates_other_profile(client: TestClient) -> None:
    user = register(client, PHONE)
    admin = register(client, ADMIN_PHONE)

    response = patch_other(client, admin, user["id"], {"name": "Мария", "telegram": "@maria_k"})

    assert response.status_code == 200
    assert response.json()["name"] == "Мария"
    assert response.json()["telegram"] == "@maria_k"


def test_admin_cannot_change_roles(client: TestClient) -> None:
    user = register(client, PHONE)
    admin = register(client, ADMIN_PHONE)
    assert patch_other(client, admin, user["id"], {"roles": ["admin"]}).status_code == 422


def test_admin_birth_date_validation(client: TestClient) -> None:
    user = register(client, PHONE)
    admin = register(client, ADMIN_PHONE)
    assert patch_other(client, admin, user["id"], {"birth_date": "2027-01-01"}).status_code == 422
    assert patch_other(client, admin, user["id"], {"birth_date": "2013-06-01"}).status_code == 422


def test_admin_updates_missing_profile(client: TestClient) -> None:
    admin = register(client, ADMIN_PHONE)
    assert patch_other(client, admin, str(uuid.uuid4()), {"name": "X"}).status_code == 404


def test_regular_user_cannot_update_other_profile(client: TestClient) -> None:
    user = register(client, PHONE)
    other = register(client, OTHER_PHONE, name="Олег")

    response = patch_other(client, user, other["id"], {"name": "Взлом"})

    assert response.status_code == 403
    assert client.get("/api/profile", headers=auth_header(other)).json()["name"] == "Олег"


def test_admin_sets_taken_phone(client: TestClient) -> None:
    user = register(client, PHONE)
    register(client, OTHER_PHONE)
    admin = register(client, ADMIN_PHONE)

    response = patch_other(client, admin, user["id"], {"phone": OTHER_PHONE})

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "phone_taken"


def test_admin_sets_taken_email_with_phone_change(client: TestClient) -> None:
    user = register(client, PHONE)
    other = register(client, OTHER_PHONE)
    admin = register(client, ADMIN_PHONE)
    patch_own(client, other, {"email": "taken@example.com"})

    response = patch_other(
        client, admin, user["id"], {"email": "taken@example.com", "phone": "+79997654321"}
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "email_taken"
    # Ничего не применилось, сессии пользователя живы
    profile = client.get("/api/profile", headers=auth_header(user)).json()
    assert profile["phone"] == PHONE
    refreshed = client.post("/api/auth/refresh", json={"refresh_token": user["refresh_token"]})
    assert refreshed.status_code == 200


def test_admin_changes_phone(client: TestClient, clock: FakeClock) -> None:
    user = register(client, PHONE)
    admin = register(client, ADMIN_PHONE)
    clock.advance(60)
    # Неиспользованный код для старого номера должен быть отменён
    client.post("/api/auth/code", json={"phone": PHONE})

    response = patch_other(client, admin, user["id"], {"phone": "8 999 765 43 21"})

    assert response.status_code == 200
    assert response.json()["phone"] == "+79997654321"
    # Сессии пользователя сброшены
    refreshed = client.post("/api/auth/refresh", json={"refresh_token": user["refresh_token"]})
    assert refreshed.status_code == 401
    # Код старого номера больше не действует
    assert client.get("/api/auth/test/code", params={"phone": PHONE}).status_code == 404

    # Вход по новому номеру попадает в того же пользователя
    new_tokens = login(client, "+79997654321")
    profile = client.get("/api/profile", headers=auth_header(new_tokens)).json()
    assert profile["id"] == user["id"]
    assert profile["name"] == "Анна"


def test_old_phone_after_change_belongs_to_nobody(client: TestClient, clock: FakeClock) -> None:
    user = register(client, PHONE)
    admin = register(client, ADMIN_PHONE)
    patch_other(client, admin, user["id"], {"phone": "+79997654321"})
    clock.advance(60)

    assert client.post("/api/auth/code", json={"phone": PHONE}).status_code == 200
    code = get_code(client, PHONE)
    tokens = client.post("/api/auth/verify", json={"phone": PHONE, "code": code}).json()

    profile = client.get("/api/profile", headers=auth_header(tokens)).json()
    assert profile["id"] != user["id"]
    assert profile["profile_completed"] is False
