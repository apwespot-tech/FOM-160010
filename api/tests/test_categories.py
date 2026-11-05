"""Справочник категорий: иконки и картинки."""

import threading
import uuid
from io import BytesIO
from typing import Any

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CategoryCover
from app.models.event import MAX_PHOTO_BYTES
from tests.conftest import ADMIN_PHONE, FakeClock, auth_header, create_event, login, register
from tests.images import jpeg_of_size, make_image

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


def test_cover_requires_token_but_not_completed_profile(client: TestClient) -> None:
    user = register(client, PHONE)
    cinema = categories(client, user)[3]
    draft = login(client, "+79991234568")
    path = f"/api/categories/{cinema['id']}/covers/{cinema['cover_id']}"

    assert client.get(path).status_code == 401
    response = client.get(path, headers=auth_header(draft))
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/webp"


def test_draft_gets_categories(client: TestClient) -> None:
    draft = login(client, PHONE)

    response = client.get("/api/categories", headers=auth_header(draft))

    assert response.status_code == 200
    assert {"Настольные игры", "Прогулки", "Спорт", "Кино"} <= {c["name"] for c in response.json()}


def test_categories_require_token(client: TestClient) -> None:
    assert client.get("/api/categories").status_code == 401


# --- изменение справочника администратором ---

OTHER = "+79991234568"


def post_category(
    client: TestClient,
    user: dict[str, Any],
    name: str = "Музеи",
    icon: str = "pi-building",
    content: bytes | None = None,
) -> Any:
    files = {"file": ("cover.jpg", content, "image/jpeg")} if content is not None else None
    return client.post(
        "/api/categories",
        data={"name": name, "icon": icon},
        files=files,
        headers=auth_header(user),
    )


def new_category(client: TestClient, admin: dict[str, Any], name: str = "Музеи") -> dict[str, Any]:
    response = post_category(client, admin, name, content=make_image("JPEG", (1600, 1200)))
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


def patch_category(
    client: TestClient, user: dict[str, Any], category_id: int, body: dict[str, Any]
) -> Any:
    return client.patch(f"/api/categories/{category_id}", json=body, headers=auth_header(user))


def put_cover(client: TestClient, user: dict[str, Any], category_id: int, content: bytes) -> Any:
    return client.put(
        f"/api/categories/{category_id}/cover",
        files={"file": ("cover.png", content, "image/png")},
        headers=auth_header(user),
    )


def test_category_dictionary_rights(client: TestClient) -> None:
    user = register(client, PHONE)
    draft = login(client, OTHER)
    image = make_image("JPEG")

    assert client.delete("/api/categories/4").status_code == 401
    forbidden = post_category(client, user, content=image)
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["code"] == "forbidden"
    incomplete = post_category(client, draft, content=image)
    assert incomplete.json()["detail"]["code"] == "profile_incomplete"
    assert patch_category(client, user, 4, {"name": "Фильмы"}).status_code == 403
    assert put_cover(client, user, 4, make_image("PNG")).status_code == 403
    assert client.delete("/api/categories/4", headers=auth_header(user)).status_code == 403
    assert len(categories(client, user)) == 4


def test_admin_creates_category(client: TestClient) -> None:
    admin = register(client, ADMIN_PHONE)

    response = post_category(client, admin, "  Музеи  ", content=make_image("JPEG", (1600, 1200)))

    assert response.status_code == 201
    created = response.json()
    assert (created["name"], created["icon"]) == ("Музеи", "pi-building")
    assert categories(client, admin)[-1] == created
    full = cover(client, admin, created["id"], created["cover_id"])
    thumb = cover(client, admin, created["id"], created["cover_id"], size="thumb")
    assert full.status_code == 200
    with Image.open(BytesIO(thumb.content)) as small:
        assert small.width <= 800


def test_category_validation(client: TestClient) -> None:
    admin = register(client, ADMIN_PHONE)
    image = make_image("JPEG")

    assert post_category(client, admin, "К" * 50, content=image).status_code == 201
    assert post_category(client, admin, "Л" * 51, content=image).status_code == 422
    assert post_category(client, admin, "   ", content=image).status_code == 422
    assert post_category(client, admin, "Квесты", "video", content=image).status_code == 422
    assert post_category(client, admin, "Квесты").status_code == 422
    assert len(categories(client, admin)) == 5


def test_category_file_checks(client: TestClient) -> None:
    admin = register(client, ADMIN_PHONE)

    exact = post_category(client, admin, "Квесты", content=jpeg_of_size(MAX_PHOTO_BYTES))
    too_large = post_category(client, admin, "Музеи", content=jpeg_of_size(MAX_PHOTO_BYTES + 1))
    not_image = post_category(client, admin, "Театр", content=b"just text")

    assert exact.status_code == 201
    assert too_large.status_code == 422
    assert too_large.json()["detail"]["code"] == "photo_too_large"
    assert not_image.status_code == 422
    assert not_image.json()["detail"]["code"] == "photo_invalid"
    assert len(categories(client, admin)) == 5


def test_rename_category_visible_in_event(client: TestClient) -> None:
    admin = register(client, ADMIN_PHONE)
    event = create_event(client, admin, category_id=4)

    response = patch_category(client, admin, 4, {"name": "Кино и сериалы", "icon": "pi-desktop"})

    assert response.status_code == 200
    assert (response.json()["name"], response.json()["icon"]) == ("Кино и сериалы", "pi-desktop")
    got = client.get(f"/api/events/{event['id']}", headers=auth_header(admin)).json()
    assert got["category"]["name"] == "Кино и сериалы"


def test_patch_category_errors(client: TestClient) -> None:
    admin = register(client, ADMIN_PHONE)

    assert patch_category(client, admin, 4, {"icon": None}).status_code == 422
    assert patch_category(client, admin, 4, {"cover_id": str(uuid.uuid4())}).status_code == 422
    assert patch_category(client, admin, 999999, {"name": "Театр"}).status_code == 404
    assert categories(client, admin)[3]["icon"] == "pi-video"


def test_category_name_unique_case_insensitive(client: TestClient) -> None:
    admin = register(client, ADMIN_PHONE)

    taken = post_category(client, admin, "кино", content=make_image("JPEG"))
    renamed_to_taken = patch_category(client, admin, 3, {"name": "КИНО"})
    own_case = patch_category(client, admin, 4, {"name": "КИНО"})

    assert taken.status_code == 409
    assert taken.json()["detail"]["code"] == "category_name_taken"
    assert renamed_to_taken.status_code == 409
    assert own_case.status_code == 200


def test_concurrent_category_create(client: TestClient) -> None:
    admin = register(client, ADMIN_PHONE)
    image = make_image("JPEG")
    barrier = threading.Barrier(2)
    statuses: list[int] = []

    def worker() -> None:
        barrier.wait()
        statuses.append(post_category(client, admin, "Музеи", content=image).status_code)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(statuses) == [201, 409]
    assert [c["name"] for c in categories(client, admin)].count("Музеи") == 1


def test_replace_category_cover(client: TestClient) -> None:
    admin = register(client, ADMIN_PHONE)
    museums = new_category(client, admin)

    response = put_cover(client, admin, museums["id"], make_image("PNG", (300, 200)))
    too_large = put_cover(client, admin, museums["id"], jpeg_of_size(3 * 1024 * 1024))

    assert response.status_code == 200
    new_cover = response.json()["cover_id"]
    assert new_cover != museums["cover_id"]
    assert cover(client, admin, museums["id"], museums["cover_id"]).status_code == 404
    assert cover(client, admin, museums["id"], new_cover).headers["content-type"] == "image/png"
    assert too_large.status_code == 422
    assert too_large.json()["detail"]["code"] == "photo_too_large"
    assert categories(client, admin)[-1]["cover_id"] == new_cover
    assert put_cover(client, admin, 999999, make_image("PNG")).status_code == 404


def test_concurrent_cover_replace(client: TestClient, db: Session) -> None:
    admin = register(client, ADMIN_PHONE)
    museums = new_category(client, admin)
    covers_before = db.scalar(select(func.count()).select_from(CategoryCover))
    barrier = threading.Barrier(2)
    statuses: list[int] = []

    def worker() -> None:
        barrier.wait()
        statuses.append(put_cover(client, admin, museums["id"], make_image("PNG")).status_code)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert statuses == [200, 200]
    assert db.scalar(select(func.count()).select_from(CategoryCover)) == covers_before


def test_delete_category_removes_interests_and_cover(client: TestClient) -> None:
    admin = register(client, ADMIN_PHONE)
    user = register(client, PHONE)
    museums = new_category(client, admin)
    client.patch(
        "/api/profile", json={"interest_ids": [1, museums["id"]]}, headers=auth_header(user)
    )

    response = client.delete(f"/api/categories/{museums['id']}", headers=auth_header(admin))

    assert response.status_code == 204
    assert museums["id"] not in {c["id"] for c in categories(client, admin)}
    interests = client.get("/api/profile", headers=auth_header(user)).json()["interests"]
    assert [i["id"] for i in interests] == [1]
    assert cover(client, admin, museums["id"], museums["cover_id"]).status_code == 404
    missing = client.delete(f"/api/categories/{museums['id']}", headers=auth_header(admin))
    assert missing.status_code == 404


def test_category_with_past_event_cannot_be_deleted(client: TestClient, clock: FakeClock) -> None:
    admin = register(client, ADMIN_PHONE)
    museums = new_category(client, admin)
    create_event(client, admin, category_id=museums["id"])
    clock.advance(3 * 24 * 3600)
    admin = login(client, ADMIN_PHONE)  # access-токен за это время истёк

    response = client.delete(f"/api/categories/{museums['id']}", headers=auth_header(admin))

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "category_in_use"
    assert museums["id"] in {c["id"] for c in categories(client, admin)}
