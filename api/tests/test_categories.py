"""Справочник категорий."""

from fastapi.testclient import TestClient

from tests.conftest import auth_header, login, register

PHONE = "+79991234567"


def test_list_categories(client: TestClient) -> None:
    user = register(client, PHONE)

    response = client.get("/api/categories", headers=auth_header(user))

    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "name": "Настольные игры"},
        {"id": 2, "name": "Прогулки"},
        {"id": 3, "name": "Спорт"},
        {"id": 4, "name": "Кино"},
    ]


def test_categories_require_completed_profile(client: TestClient) -> None:
    draft = login(client, PHONE)

    response = client.get("/api/categories", headers=auth_header(draft))

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "profile_incomplete"


def test_categories_require_token(client: TestClient) -> None:
    assert client.get("/api/categories").status_code == 401
