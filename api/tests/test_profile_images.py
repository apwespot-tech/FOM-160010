"""Аватар и обложка профиля: загрузка, замена, удаление, отдача, одновременность."""

import threading
from io import BytesIO
from typing import Any

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import UserImage
from app.models.event import MAX_PHOTO_BYTES
from tests.conftest import (
    auth_header,
    create_event,
    login,
    register,
    upload_avatar,
)
from tests.images import jpeg_of_size, make_image

ANNA = "+79991234567"
BORIS = "+79991234568"


def upload(client: TestClient, user: dict[str, Any], kind: str, content: bytes) -> Any:
    return client.put(
        f"/api/profile/{kind}",
        files={"file": ("me.jpg", content, "image/jpeg")},
        headers=auth_header(user),
    )


def image(client: TestClient, viewer: dict[str, Any], user_id: str, image_id: str, **p: Any) -> Any:
    return client.get(
        f"/api/users/{user_id}/images/{image_id}", params=p, headers=auth_header(viewer)
    )


def count_images(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(UserImage)) or 0


def test_upload_and_replace_avatar(client: TestClient) -> None:
    anna = register(client, ANNA)

    first = upload_avatar(client, anna)
    second = upload_avatar(client, anna, make_image("PNG", (50, 50)))

    assert first != second
    assert image(client, anna, anna["id"], first).status_code == 404
    response = image(client, anna, anna["id"], second)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "private, max-age=31536000, immutable"


def test_upload_and_delete_cover(client: TestClient, db: Session) -> None:
    anna = register(client, ANNA)
    uploaded = upload(client, anna, "cover", make_image("JPEG", (2000, 500)))
    cover_id = uploaded.json()["cover_id"]

    deleted = client.delete("/api/profile/cover", headers=auth_header(anna))

    assert uploaded.status_code == 200 and cover_id
    assert deleted.status_code == 200
    assert deleted.json()["cover_id"] is None
    assert image(client, anna, anna["id"], cover_id).status_code == 404
    assert count_images(db) == 0


def test_size_boundary(client: TestClient) -> None:
    anna = register(client, ANNA)
    exact = upload(client, anna, "avatar", jpeg_of_size(MAX_PHOTO_BYTES))

    over = upload(client, anna, "avatar", jpeg_of_size(MAX_PHOTO_BYTES + 1))

    assert exact.status_code == 200
    assert over.status_code == 422
    assert over.json()["detail"]["code"] == "photo_too_large"
    current = client.get("/api/profile", headers=auth_header(anna)).json()
    assert current["avatar_id"] == exact.json()["avatar_id"]


def test_not_an_image(client: TestClient) -> None:
    anna = register(client, ANNA)

    response = upload(client, anna, "avatar", b"just text")

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "photo_invalid"
    assert client.get("/api/profile", headers=auth_header(anna)).json()["avatar_id"] is None


def test_draft_cannot_upload(client: TestClient) -> None:
    draft = login(client, ANNA)

    response = upload(client, draft, "avatar", make_image("JPEG"))

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "profile_incomplete"


def test_concurrent_uploads_leave_one_image(client: TestClient, db: Session) -> None:
    anna = register(client, ANNA)
    barrier = threading.Barrier(2)
    results: list[Any] = [None, None]

    def worker(index: int) -> None:
        barrier.wait()
        results[index] = upload(
            client, anna, "avatar", make_image("JPEG", color=(index * 90, 0, 0))
        )

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert [r.status_code for r in results] == [200, 200]
    final = client.get("/api/profile", headers=auth_header(anna)).json()["avatar_id"]
    assert final in {r.json()["avatar_id"] for r in results}
    assert count_images(db) == 1


def test_organizer_avatar_visible_to_outsider(client: TestClient) -> None:
    anna = register(client, ANNA)
    boris = register(client, BORIS)
    upload_avatar(client, anna, make_image("JPEG", (1600, 1200)))
    event = create_event(client, anna)
    avatar_id = client.get(f"/api/events/{event['id']}", headers=auth_header(boris)).json()[
        "organizer"
    ]["avatar_id"]

    full = image(client, boris, anna["id"], avatar_id)
    thumb = image(client, boris, anna["id"], avatar_id, size="thumb")

    assert full.status_code == 200
    assert thumb.status_code == 200
    assert thumb.headers["content-type"] == "image/webp"
    with Image.open(BytesIO(thumb.content)) as small:
        assert small.size[0] <= 800


def test_image_of_other_user_and_access(client: TestClient) -> None:
    anna = register(client, ANNA)
    boris = register(client, BORIS)
    avatar_id = upload_avatar(client, anna)

    assert image(client, boris, boris["id"], avatar_id).status_code == 404
    assert image(client, boris, anna["id"], avatar_id, size="huge").status_code == 422
    assert client.get(f"/api/users/{anna['id']}/images/{avatar_id}").status_code == 401
