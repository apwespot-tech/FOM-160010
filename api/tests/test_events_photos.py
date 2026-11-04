"""Фото мероприятий: представление, отдача, замена набора, права, одновременность."""

import json
import threading
from datetime import timedelta
from io import BytesIO
from typing import Any

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import EventPhoto, EventPhotoData
from app.models.event import MAX_PHOTO_BYTES
from tests.conftest import (
    ADMIN_PHONE,
    START,
    FakeClock,
    auth_header,
    create_event,
    join,
    login,
    register,
)
from tests.images import jpeg_of_size, make_image

ORGANIZER = "+79997770001"
OTHER = "+79997770002"


def error_code(response: Any) -> str:
    code: str = response.json()["detail"]["code"]
    return code


def put_photos(
    client: TestClient,
    user: dict[str, Any],
    event_id: str,
    order: list[dict[str, Any]],
    files: list[bytes] | None = None,
    *,
    raw_order: str | None = None,
) -> Any:
    multipart = [
        ("files", (f"photo{index}.jpg", content, "image/jpeg"))
        for index, content in enumerate(files or [])
    ]
    return client.put(
        f"/api/events/{event_id}/photos",
        data={"order": raw_order if raw_order is not None else json.dumps(order)},
        files=multipart or None,
        headers=auth_header(user),
    )


def new_files(count: int) -> tuple[list[dict[str, Any]], list[bytes]]:
    """Порядок из count новых файлов и сами файлы (разного цвета, чтобы различались)."""
    files = [make_image("JPEG", color=(index * 20, 100, 50)) for index in range(count)]
    return [{"file": index} for index in range(count)], files


def photo_ids(event: dict[str, Any]) -> list[str]:
    return [photo["id"] for photo in event["photos"]]


def get_photo(client: TestClient, user: dict[str, Any], event_id: str, photo_id: str) -> Any:
    return client.get(f"/api/events/{event_id}/photos/{photo_id}", headers=auth_header(user))


def count_photos(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(EventPhoto)) or 0


def event_with_photos(
    client: TestClient, organizer: dict[str, Any], count: int, **overrides: Any
) -> dict[str, Any]:
    event = create_event(client, organizer, **overrides)
    if count:
        order, files = new_files(count)
        response = put_photos(client, organizer, event["id"], order, files)
        assert response.status_code == 200, response.text
        event = response.json()
    return event


# --- представление ---


def test_new_event_has_no_photos(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    event = create_event(client, organizer)
    assert event["photos"] == []


def test_photos_in_event_and_catalog(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    other = register(client, OTHER)
    event = event_with_photos(client, organizer, 3)
    ids = photo_ids(event)
    assert len(ids) == 3
    assert set(event["photos"][0]) == {"id"}

    single = client.get(f"/api/events/{event['id']}", headers=auth_header(other)).json()
    catalog = client.get("/api/events", headers=auth_header(other)).json()
    assert photo_ids(single) == ids
    assert photo_ids(catalog["items"][0]) == ids


# --- отдача ---


def test_get_photo_for_not_joined_user(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    other = register(client, OTHER)
    event = create_event(client, organizer)
    original = make_image("PNG", (10, 10))
    saved = put_photos(client, organizer, event["id"], [{"file": 0}], [original]).json()

    response = get_photo(client, other, event["id"], photo_ids(saved)[0])

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "private, max-age=31536000, immutable"
    assert response.headers["x-content-type-options"] == "nosniff"
    with Image.open(BytesIO(response.content)) as image:
        assert image.format == "PNG"
        assert image.size == (10, 10)


def test_get_photo_of_past_event(client: TestClient, clock: FakeClock) -> None:
    organizer = register(client, ORGANIZER)
    event = event_with_photos(client, organizer, 1)
    clock.advance(timedelta(days=2).total_seconds())
    # Прежний access-токен истёк вместе с часами — входим заново
    fresh = login(client, ORGANIZER)

    response = get_photo(client, fresh, event["id"], photo_ids(event)[0])

    assert response.status_code == 200


def test_photo_of_other_event_is_not_found(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    first = event_with_photos(client, organizer, 1)
    second = create_event(client, organizer)

    response = get_photo(client, organizer, second["id"], photo_ids(first)[0])

    assert response.status_code == 404
    assert error_code(response) == "photo_not_found"


def test_get_photo_requires_token(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    event = event_with_photos(client, organizer, 1)

    response = client.get(f"/api/events/{event['id']}/photos/{photo_ids(event)[0]}")

    assert response.status_code == 401


def test_get_photo_requires_completed_profile(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    event = event_with_photos(client, organizer, 1)
    draft = login(client, OTHER)

    response = get_photo(client, draft, event["id"], photo_ids(event)[0])

    assert response.status_code == 403
    assert error_code(response) == "profile_incomplete"


# --- замена набора ---


def test_add_to_existing(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    event = event_with_photos(client, organizer, 2)
    first, second = photo_ids(event)

    response = put_photos(
        client,
        organizer,
        event["id"],
        [{"id": first}, {"id": second}, {"file": 0}],
        [make_image("WEBP")],
    )

    assert response.status_code == 200
    ids = photo_ids(response.json())
    assert ids[:2] == [first, second]
    assert len(ids) == 3
    new_photo = get_photo(client, organizer, event["id"], ids[2])
    assert new_photo.headers["content-type"] == "image/webp"


def test_change_main_photo_keeps_ids(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    event = event_with_photos(client, organizer, 3)
    a, b, c = photo_ids(event)

    response = put_photos(client, organizer, event["id"], [{"id": c}, {"id": a}, {"id": b}])

    assert response.status_code == 200
    assert photo_ids(response.json()) == [c, a, b]


def test_empty_list_removes_all(client: TestClient, db: Session) -> None:
    organizer = register(client, ORGANIZER)
    event = event_with_photos(client, organizer, 2)
    old_ids = photo_ids(event)

    response = put_photos(client, organizer, event["id"], [])

    assert response.status_code == 200
    assert response.json()["photos"] == []
    assert count_photos(db) == 0
    assert db.scalar(select(func.count()).select_from(EventPhotoData)) == 0
    for photo_id in old_ids:
        assert get_photo(client, organizer, event["id"], photo_id).status_code == 404


def test_ten_photos_pass(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    event = event_with_photos(client, organizer, 10)
    assert len(event["photos"]) == 10


def test_eleven_photos_are_rejected(client: TestClient, db: Session) -> None:
    organizer = register(client, ORGANIZER)
    event = event_with_photos(client, organizer, 4)
    kept = [{"id": photo_id} for photo_id in photo_ids(event)]
    order, files = new_files(7)

    response = put_photos(client, organizer, event["id"], kept + order, files)

    assert response.status_code == 422
    assert error_code(response) == "too_many_photos"
    assert count_photos(db) == 4


def test_exactly_two_megabytes_passes(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    event = create_event(client, organizer)

    response = put_photos(
        client, organizer, event["id"], [{"file": 0}], [jpeg_of_size(MAX_PHOTO_BYTES)]
    )

    assert response.status_code == 200
    assert len(response.json()["photos"]) == 1


def test_one_byte_over_two_megabytes_is_rejected(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    event = create_event(client, organizer)
    order, files = new_files(1)

    response = put_photos(
        client,
        organizer,
        event["id"],
        [*order, {"file": 1}],
        [*files, jpeg_of_size(MAX_PHOTO_BYTES + 1)],
    )

    assert response.status_code == 422
    assert error_code(response) == "photo_too_large"
    assert response.json()["detail"]["file"] == 1


def test_text_with_jpg_name_is_rejected(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    event = create_event(client, organizer)

    response = put_photos(client, organizer, event["id"], [{"file": 0}], [b"not an image"])

    assert response.status_code == 422
    assert error_code(response) == "photo_invalid"
    assert response.json()["detail"]["file"] == 0


def test_gif_is_rejected(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    event = create_event(client, organizer)

    response = put_photos(client, organizer, event["id"], [{"file": 0}], [make_image("GIF")])

    assert response.status_code == 422
    assert error_code(response) == "photo_invalid"


def test_error_in_one_file_saves_nothing(client: TestClient, db: Session) -> None:
    organizer = register(client, ORGANIZER)
    event = event_with_photos(client, organizer, 1)
    (kept,) = photo_ids(event)

    response = put_photos(
        client,
        organizer,
        event["id"],
        [{"id": kept}, {"file": 0}, {"file": 1}],
        [make_image("JPEG"), jpeg_of_size(MAX_PHOTO_BYTES + 1)],
    )

    assert response.status_code == 422
    assert error_code(response) == "photo_too_large"
    assert count_photos(db) == 1
    current = client.get(f"/api/events/{event['id']}", headers=auth_header(organizer)).json()
    assert photo_ids(current) == [kept]


def test_photo_of_other_event_in_list(client: TestClient, db: Session) -> None:
    organizer = register(client, ORGANIZER)
    foreign = event_with_photos(client, organizer, 1)
    event = event_with_photos(client, organizer, 1)

    response = put_photos(
        client,
        organizer,
        event["id"],
        [{"id": photo_ids(foreign)[0]}, *[{"id": photo_ids(event)[0]}]],
    )

    assert response.status_code == 422
    assert error_code(response) == "photo_list_invalid"
    assert count_photos(db) == 2


def test_invalid_lists(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    event = event_with_photos(client, organizer, 1)
    (photo_id,) = photo_ids(event)
    image = make_image("JPEG")

    cases: list[tuple[list[dict[str, Any]], list[bytes]]] = [
        ([{"id": photo_id}, {"id": photo_id}], []),  # повтор фото
        ([{"id": photo_id}], [image]),  # файл не использован
        ([{"file": 0}, {"file": 0}], [image]),  # файл дважды
        ([{"file": 1}], [image]),  # нет такого файла
        ([{"id": "not-a-uuid"}], []),
        ([{"other": 1}], []),
    ]
    for order, files in cases:
        response = put_photos(client, organizer, event["id"], order, files)
        assert response.status_code == 422, order
        assert error_code(response) == "photo_list_invalid", order

    broken = put_photos(client, organizer, event["id"], [], raw_order="{not json")
    assert broken.status_code == 422
    assert error_code(broken) == "photo_list_invalid"


# --- права ---


def test_admin_changes_foreign_event_photos(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    admin = register(client, ADMIN_PHONE)
    event = create_event(client, organizer)
    order, files = new_files(1)

    response = put_photos(client, admin, event["id"], order, files)

    assert response.status_code == 200
    assert len(response.json()["photos"]) == 1


def test_participant_cannot_change_photos(client: TestClient, db: Session) -> None:
    organizer = register(client, ORGANIZER)
    participant = register(client, OTHER)
    event = event_with_photos(client, organizer, 1)
    join(client, participant, event["id"])

    for files in ([make_image("JPEG")], [b"broken file"]):
        response = put_photos(client, participant, event["id"], [{"file": 0}], files)
        assert response.status_code == 403
        assert error_code(response) == "forbidden"
    assert count_photos(db) == 1


def test_started_event_photos_are_frozen(client: TestClient, clock: FakeClock) -> None:
    organizer = register(client, ORGANIZER)
    event = create_event(client, organizer, starts_at=(START + timedelta(minutes=10)).isoformat())
    clock.advance(timedelta(minutes=10).total_seconds())
    order, files = new_files(1)

    response = put_photos(client, organizer, event["id"], order, files)

    assert response.status_code == 409
    assert error_code(response) == "event_started"


def test_change_photos_one_second_before_start(client: TestClient, clock: FakeClock) -> None:
    organizer = register(client, ORGANIZER)
    event = create_event(client, organizer, starts_at=(START + timedelta(minutes=10)).isoformat())
    clock.advance(timedelta(minutes=10).total_seconds() - 1)
    order, files = new_files(1)

    response = put_photos(client, organizer, event["id"], order, files)

    assert response.status_code == 200


def test_unknown_event(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    order, files = new_files(1)

    response = put_photos(client, organizer, "00000000-0000-0000-0000-000000000000", order, files)

    assert response.status_code == 404


def test_put_photos_requires_token(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    event = create_event(client, organizer)

    response = client.put(f"/api/events/{event['id']}/photos", data={"order": "[]"})

    assert response.status_code == 401


# --- удаление мероприятия и одновременность ---


def test_photos_deleted_with_event(client: TestClient, db: Session) -> None:
    organizer = register(client, ORGANIZER)
    event = event_with_photos(client, organizer, 2)

    assert (
        client.delete(f"/api/events/{event['id']}", headers=auth_header(organizer)).status_code
        == 204
    )

    assert count_photos(db) == 0
    for photo_id in photo_ids(event):
        assert get_photo(client, organizer, event["id"], photo_id).status_code == 404


def run_concurrently(*actions: Any) -> list[Any]:
    barrier = threading.Barrier(len(actions))
    results: list[Any] = [None] * len(actions)

    def worker(index: int) -> None:
        barrier.wait()
        results[index] = actions[index]()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(len(actions))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results


def test_concurrent_replacements_never_exceed_limit(client: TestClient, db: Session) -> None:
    organizer = register(client, ORGANIZER)
    admin = register(client, ADMIN_PHONE)
    event = event_with_photos(client, organizer, 4)
    kept = [{"id": photo_id} for photo_id in photo_ids(event)]
    order, files = new_files(6)
    new_order = [{"file": item["file"]} for item in order]

    results = run_concurrently(
        lambda: put_photos(client, organizer, event["id"], kept + new_order, files),
        lambda: put_photos(client, admin, event["id"], kept + new_order, files),
    )

    assert [r.status_code for r in results] == [200, 200]
    final = client.get(f"/api/events/{event['id']}", headers=auth_header(organizer)).json()
    assert count_photos(db) == 10
    assert photo_ids(final)[:4] == [item["id"] for item in kept]
    # Итог — набор одного из запросов целиком
    assert photo_ids(final) in [photo_ids(r.json()) for r in results]


def test_replacement_with_concurrent_delete(client: TestClient, db: Session) -> None:
    organizer = register(client, ORGANIZER)
    admin = register(client, ADMIN_PHONE)
    event = event_with_photos(client, organizer, 1)
    order, files = new_files(3)

    put_result, delete_result = run_concurrently(
        lambda: put_photos(client, organizer, event["id"], order, files),
        lambda: client.delete(f"/api/events/{event['id']}", headers=auth_header(admin)),
    )

    assert delete_result.status_code == 204
    assert put_result.status_code in (200, 404)
    assert count_photos(db) == 0
    assert db.scalar(select(func.count()).select_from(EventPhotoData)) == 0
