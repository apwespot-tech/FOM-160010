"""Реестр доступа пользователя с незаполненным профилем ко всем ручкам API.

Черновику открыты только ручки просмотра; всё остальное — 403 `profile_incomplete`.
Новая ручка, не добавленная в списки ниже, роняет тест: решение о доступе принимается явно.
"""

import re

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.conftest import auth_header, login

DRAFT = "+79991234567"
MISSING_ID = "00000000-0000-0000-0000-000000000000"

# Не требуют токена
PUBLIC = {
    ("POST", "/api/auth/code"),
    ("GET", "/api/auth/test/code"),
    ("POST", "/api/auth/verify"),
    ("POST", "/api/auth/refresh"),
    ("POST", "/api/auth/logout"),
}

# Доступны черновику
OPEN_TO_DRAFT = {
    ("GET", "/api/profile"),
    ("PATCH", "/api/profile"),
    ("GET", "/api/categories"),
    ("GET", "/api/categories/{category_id}/covers/{cover_id}"),
    ("GET", "/api/cities"),
    ("GET", "/api/events"),
    ("GET", "/api/events/{event_id}"),
    ("GET", "/api/events/{event_id}/photos/{photo_id}"),
    ("GET", "/api/users/{user_id}/images/{image_id}"),
}

PARAM_VALUES = {"category_id": "1", "kind": "avatar"}


def all_endpoints(app: FastAPI) -> set[tuple[str, str]]:
    paths = app.openapi()["paths"]
    return {(method.upper(), path) for path, item in paths.items() for method in item}


def concrete(path: str) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: PARAM_VALUES.get(m.group(1), MISSING_ID), path)


def test_registry_covers_every_endpoint(app: FastAPI) -> None:
    endpoints = all_endpoints(app)

    assert endpoints >= PUBLIC | OPEN_TO_DRAFT
    # Ручек, требующих заполненного профиля, больше нуля — проверяются ниже
    assert endpoints - PUBLIC - OPEN_TO_DRAFT


def test_draft_access(app: FastAPI, client: TestClient) -> None:
    headers = auth_header(login(client, DRAFT))
    allowed: set[tuple[str, str]] = set()
    denied: set[tuple[str, str]] = set()

    for method, path in sorted(all_endpoints(app) - PUBLIC):
        response = client.request(method, concrete(path), json={}, headers=headers)
        detail = response.json().get("detail") if response.status_code == 403 else None
        incomplete = isinstance(detail, dict) and detail.get("code") == "profile_incomplete"
        (denied if incomplete else allowed).add((method, path))

    assert allowed == OPEN_TO_DRAFT
    assert {("POST", "/api/events"), ("POST", "/api/events/{event_id}/join")} <= denied
    assert ("GET", "/api/events/{event_id}/participants") in denied
    assert ("PUT", "/api/profile/{kind}") in denied
    assert ("GET", "/api/profile/{user_id}") in denied
