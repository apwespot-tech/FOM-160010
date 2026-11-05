"""Удаление записей справочников одновременно со ссылками на них (мероприятия, профили)."""

import threading
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.services import event_service
from tests.conftest import ADMIN_PHONE, auth_header, event_payload, register
from tests.images import make_image

USER = "+79991234567"


def run_together(*actions: Callable[[], Any]) -> list[Any]:
    """Запускает действия одновременно и возвращает их результаты по порядку."""
    barrier = threading.Barrier(len(actions))
    results: list[Any] = [None] * len(actions)

    def worker(index: int, action: Callable[[], Any]) -> None:
        barrier.wait()
        results[index] = action()

    threads = [threading.Thread(target=worker, args=item) for item in enumerate(actions)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results


def new_city(client: TestClient, admin: dict[str, Any], name: str = "Тверь") -> int:
    response = client.post("/api/cities", json={"name": name}, headers=auth_header(admin))
    assert response.status_code == 201, response.text
    city_id: int = response.json()["id"]
    return city_id


def new_category(client: TestClient, admin: dict[str, Any]) -> int:
    response = client.post(
        "/api/categories",
        data={"name": "Музеи", "icon": "pi-building"},
        files={"file": ("c.jpg", make_image("JPEG"), "image/jpeg")},
        headers=auth_header(admin),
    )
    assert response.status_code == 201, response.text
    category_id: int = response.json()["id"]
    return category_id


def error_code(response: Any) -> str | None:
    detail = response.json().get("detail") if response.content else None
    return detail.get("code") if isinstance(detail, dict) else None


def test_event_with_deleted_category_is_not_found(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Проверка прошла, а категорию удалили до записи: ссылку отклоняет внешний ключ."""
    user = register(client, USER)
    monkeypatch.setattr(event_service, "_ensure_category_exists", lambda *_: None)
    monkeypatch.setattr(event_service, "_ensure_city_exists", lambda *_: None)

    category = client.post(
        "/api/events", json=event_payload(category_id=999999), headers=auth_header(user)
    )
    city = client.post("/api/events", json=event_payload(city_id=999999), headers=auth_header(user))

    assert (category.status_code, error_code(category)) == (422, "category_not_found")
    assert (city.status_code, error_code(city)) == (422, "city_not_found")


@pytest.mark.parametrize("kind", ["category", "city"])
def test_delete_while_event_created(client: TestClient, kind: str) -> None:
    admin = register(client, ADMIN_PHONE)
    user = register(client, USER)
    if kind == "category":
        record = new_category(client, admin)
        path, payload = f"/api/categories/{record}", event_payload(category_id=record)
    else:
        record = new_city(client, admin)
        path, payload = f"/api/cities/{record}", event_payload(city_id=record)

    deleted, created = run_together(
        lambda: client.delete(path, headers=auth_header(admin)),
        lambda: client.post("/api/events", json=payload, headers=auth_header(user)),
    )

    outcome = (deleted.status_code, created.status_code)
    assert outcome in {(409, 201), (204, 422)}, (deleted.text, created.text)
    if outcome == (409, 201):
        assert error_code(deleted) == f"{kind}_in_use"
    else:
        assert error_code(created) == f"{kind}_not_found"


def test_delete_city_while_profile_saved(client: TestClient) -> None:
    admin = register(client, ADMIN_PHONE)
    user = register(client, USER)
    city = new_city(client, admin)

    deleted, saved = run_together(
        lambda: client.delete(f"/api/cities/{city}", headers=auth_header(admin)),
        lambda: client.patch("/api/profile", json={"city_id": city}, headers=auth_header(user)),
    )

    assert deleted.status_code == 204
    assert saved.status_code in {200, 422}
    if saved.status_code == 422:
        assert error_code(saved) == "city_not_found"
    assert client.get("/api/profile", headers=auth_header(user)).json()["city"] is None


def test_delete_category_while_interest_saved(client: TestClient) -> None:
    admin = register(client, ADMIN_PHONE)
    user = register(client, USER)
    category = new_category(client, admin)

    deleted, saved = run_together(
        lambda: client.delete(f"/api/categories/{category}", headers=auth_header(admin)),
        lambda: client.patch(
            "/api/profile", json={"interest_ids": [category]}, headers=auth_header(user)
        ),
    )

    assert deleted.status_code == 204
    assert saved.status_code in {200, 422}
    if saved.status_code == 422:
        assert error_code(saved) == "category_not_found"
    assert client.get("/api/profile", headers=auth_header(user)).json()["interests"] == []
