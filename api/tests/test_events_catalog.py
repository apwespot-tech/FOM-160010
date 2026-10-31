"""Каталог предстоящих мероприятий: фильтры, сортировка, пагинация."""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import START, FakeClock, auth_header, create_event, register

ORGANIZER = "+79991234567"
OTHER = "+79991234568"


def catalog(client: TestClient, user: dict[str, Any], **params: Any) -> Any:
    return client.get("/api/events", params=params, headers=auth_header(user))


def at(days: float) -> str:
    return (START + timedelta(days=days)).isoformat()


def test_only_upcoming_sorted_by_start(client: TestClient, clock: FakeClock) -> None:
    organizer = register(client, ORGANIZER)
    create_event(client, organizer, title="Скоро прошло", starts_at=at(0.004))  # ~6 минут
    later = create_event(client, organizer, title="Позже", starts_at=at(3))
    sooner = create_event(client, organizer, title="Раньше", starts_at=at(1))
    clock.advance(10 * 60)

    response = catalog(client, organizer)

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == [sooner["id"], later["id"]]
    assert body["total"] == 2


def test_same_start_ordered_by_id(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    ids = sorted(create_event(client, organizer, starts_at=at(1))["id"] for _ in range(3))

    items = catalog(client, organizer).json()["items"]

    assert [item["id"] for item in items] == ids


def test_filter_by_category(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    create_event(client, organizer, category_id=1)
    sport = create_event(client, organizer, category_id=3)

    body = catalog(client, organizer, category_id=3).json()

    assert [item["id"] for item in body["items"]] == [sport["id"]]
    assert body["items"][0]["category"] == {"id": 3, "name": "Спорт"}
    assert body["total"] == 1


def test_filter_by_date_range(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    day_start = datetime(2026, 12, 1, tzinfo=UTC)
    first = create_event(client, organizer, starts_at=day_start.isoformat())
    evening = create_event(
        client, organizer, starts_at=(day_start + timedelta(hours=19)).isoformat()
    )
    create_event(client, organizer, starts_at=(day_start + timedelta(days=1)).isoformat())
    create_event(client, organizer, starts_at=(day_start - timedelta(minutes=1)).isoformat())

    body = catalog(
        client,
        organizer,
        **{"from": day_start.isoformat(), "to": (day_start + timedelta(days=1)).isoformat()},
    ).json()

    assert [item["id"] for item in body["items"]] == [first["id"], evening["id"]]
    assert body["total"] == 2


def test_pagination(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    for index in range(25):
        create_event(client, organizer, starts_at=at(1 + index))

    first_page = catalog(client, organizer).json()
    last_page = catalog(client, organizer, limit=10, offset=20).json()
    beyond = catalog(client, organizer, offset=100).json()

    assert len(first_page["items"]) == 20
    assert len(last_page["items"]) == 5
    assert last_page["total"] == 25
    assert beyond == {"items": [], "total": 25}


def test_invalid_pagination(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    for params in ({"limit": 101}, {"limit": 0}, {"offset": -1}, {"from": "2026-12-01T00:00:00"}):
        assert catalog(client, organizer, **params).status_code == 422, params


def test_catalog_item_fields_for_viewer(client: TestClient) -> None:
    organizer = register(client, ORGANIZER, name="Анна")
    other = register(client, OTHER)
    create_event(client, organizer, max_participants=3)

    item = catalog(client, other).json()["items"][0]

    assert item["organizer"] == {"id": organizer["id"], "name": "Анна"}
    assert item["participants_count"] == 1
    assert item["free_places"] == 2
    assert item["is_full"] is False
    assert item["is_joined"] is False
