"""Справочник категорий: иконки и картинки."""

import uuid
from io import BytesIO
from typing import Any

from fastapi.testclient import TestClient
from PIL import Image

from tests.conftest import auth_header, create_event, login, register

PHONE = "+79991234567"
ICONS = {1: "pi-th-large", 2: "pi-map", 3: "pi-bolt", 4: "pi-video"}


def categories(client: TestClient, user: dict[str, Any]) -> list[dict[str, Any]]:
    response = client.get("/api/categories", headers=auth_header(user))
    assert response.status_code == 200
    result: list[dict[str, Any]] = response.json()
    return result


def cover(
    client: TestClient, user: dict[str, Any], category_id: int, cover_id: str, **p: Any
) -> Any:
    return client.get(
        f"/api/categories/{category_id}/covers/{cover_id}", params=p, headers=auth_header(user)
    )


def test_list_categories(client: TestClient) -> None:
    user = register(client, PHONE)

    items = categories(client, user)

    assert [(c["id"], c["name"], c["icon"]) for c in items] == [
        (1, "Настольные игры", "pi-th-large"),
        (2, "Прогулки", "pi-map"),
        (3, "Спорт", "pi-bolt"),
        (4, "Кино", "pi-video"),
    ]
    assert all(set(c) == {"id", "name", "icon", "cover_id"} for c in items)
    assert len({c["cover_id"] for c in items}) == 4


def test_category_in_event_matches_catalog(client: TestClient) -> None:
    user = register(client, PHONE)
    cinema = next(c for c in categories(client, user) if c["name"] == "Кино")

    event = create_event(client, user, category_id=cinema["id"])

    assert event["category"] == cinema


def test_category_cover(client: TestClient) -> None:
    user = register(client, PHONE)
    cinema = categories(client, user)[3]

    full = cover(client, user, cinema["id"], cinema["cover_id"])
    thumb = cover(client, user, cinema["id"], cinema["cover_id"], size="thumb")

    for response in (full, thumb):
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/webp"
        assert response.headers["cache-control"] == "private, max-age=31536000, immutable"
    with Image.open(BytesIO(full.content)) as image:
        assert image.size == (1200, 675)
    with Image.open(BytesIO(thumb.content)) as image:
        assert image.size[0] <= 800


def test_cover_of_other_category_is_not_found(client: TestClient) -> None:
    user = register(client, PHONE)
    items = categories(client, user)
    sport, cinema = items[2], items[3]

    response = cover(client, user, cinema["id"], sport["cover_id"])

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "cover_not_found"


def test_cover_of_unknown_category(client: TestClient) -> None:
    user = register(client, PHONE)

    assert cover(client, user, 999, str(uuid.uuid4())).status_code == 404


def test_cover_invalid_size(client: TestClient) -> None:
    user = register(client, PHONE)
    cinema = categories(client, user)[3]

    assert cover(client, user, cinema["id"], cinema["cover_id"], size="huge").status_code == 422


def test_cover_requires_token_and_completed_profile(client: TestClient) -> None:
    user = register(client, PHONE)
    cinema = categories(client, user)[3]
    draft = login(client, "+79991234568")
    path = f"/api/categories/{cinema['id']}/covers/{cinema['cover_id']}"

    assert client.get(path).status_code == 401
    response = client.get(path, headers=auth_header(draft))
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "profile_incomplete"


def test_categories_require_completed_profile(client: TestClient) -> None:
    draft = login(client, PHONE)

    response = client.get("/api/categories", headers=auth_header(draft))

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "profile_incomplete"


def test_categories_require_token(client: TestClient) -> None:
    assert client.get("/api/categories").status_code == 401
