"""Каталог предстоящих мероприятий: фильтры, сортировка, пагинация."""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import START, FakeClock, auth_header, create_event, login, register

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

    assert item["organizer"] == {
        "id": organizer["id"],
        "name": "Анна",
        "photo_url": None,
        "telegram": None,
    }
    assert item["participants_count"] == 1
    assert item["free_places"] == 2
    assert item["is_full"] is False
    assert item["is_joined"] is False


# --- scope: участвую / организую ---


def ids(response: Any) -> list[str]:
    return [item["id"] for item in response.json()["items"]]


def test_scope_joined_and_organized(client: TestClient) -> None:
    me = register(client, ORGANIZER)
    other = register(client, OTHER)
    mine = create_event(client, me, title="A")
    joined = create_event(client, other, title="B")
    create_event(client, other, title="C")
    client.post(f"/api/events/{joined['id']}/join", headers=auth_header(me))

    joined_response = catalog(client, me, scope="joined")
    organized_response = catalog(client, me, scope="organized")

    assert ids(joined_response) == [joined["id"]]
    assert joined_response.json()["total"] == 1
    assert ids(organized_response) == [mine["id"]]
    assert len(catalog(client, me, scope="all").json()["items"]) == 3


def test_scope_joined_after_leave(client: TestClient) -> None:
    me = register(client, ORGANIZER)
    other = register(client, OTHER)
    event = create_event(client, other)
    client.post(f"/api/events/{event['id']}/join", headers=auth_header(me))
    client.post(f"/api/events/{event['id']}/leave", headers=auth_header(me))

    assert ids(catalog(client, me, scope="joined")) == []


def test_scope_with_category_filter(client: TestClient) -> None:
    me = register(client, ORGANIZER)
    create_event(client, me, category_id=1)
    sport = create_event(client, me, category_id=3)

    assert ids(catalog(client, me, scope="organized", category_id=3)) == [sport["id"]]


def test_unknown_scope(client: TestClient) -> None:
    me = register(client, ORGANIZER)
    assert catalog(client, me, scope="mine").status_code == 422


# --- period: прошедшие ---


def test_past_organized_sorted_desc(client: TestClient, clock: FakeClock) -> None:
    me = register(client, ORGANIZER)
    week_ago = create_event(client, me, starts_at=at(1))
    yesterday = create_event(client, me, starts_at=at(7))
    upcoming = create_event(client, me, starts_at=at(20))
    clock.advance(8 * 24 * 3600)
    me = login(client, ORGANIZER)  # прежний access-токен истёк

    past = catalog(client, me, scope="organized", period="past")
    future = catalog(client, me, scope="organized")

    assert ids(past) == [yesterday["id"], week_ago["id"]]
    assert past.json()["total"] == 2
    assert ids(future) == [upcoming["id"]]


def test_event_at_start_moment_is_past(client: TestClient, clock: FakeClock) -> None:
    me = register(client, ORGANIZER)
    event = create_event(client, me, starts_at=(START + timedelta(minutes=10)).isoformat())
    clock.advance(10 * 60)

    assert ids(catalog(client, me, scope="organized", period="past")) == [event["id"]]
    assert ids(catalog(client, me, scope="organized")) == []


def test_past_joined(client: TestClient, clock: FakeClock) -> None:
    me = register(client, ORGANIZER)
    other = register(client, OTHER)
    event = create_event(client, other, starts_at=(START + timedelta(minutes=10)).isoformat())
    client.post(f"/api/events/{event['id']}/join", headers=auth_header(me))
    clock.advance(11 * 60)

    assert ids(catalog(client, me, scope="joined", period="past")) == [event["id"]]


def test_past_requires_own_scope(client: TestClient) -> None:
    me = register(client, ORGANIZER)

    for params in ({"period": "past"}, {"scope": "all", "period": "past"}):
        response = catalog(client, me, **params)
        assert response.status_code == 422, params
        assert response.json()["detail"]["code"] == "past_requires_scope"
    assert catalog(client, me, scope="joined", period="today").status_code == 422


# --- возрастной фильтр общего каталога (START = 2026-10-31) ---


def test_age_filter_for_teen(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    teen = register(client, OTHER, birth_date="2012-05-01")  # 14 лет
    allowed = [create_event(client, organizer, min_age=age)["id"] for age in (0, 14)]
    for age in (16, 18):
        create_event(client, organizer, min_age=age)

    response = catalog(client, teen)

    assert sorted(ids(response)) == sorted(allowed)
    assert response.json()["total"] == 2


def test_age_filter_birthday_today(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    adult = register(client, OTHER, birth_date="2008-10-31")  # 18 сегодня
    event = create_event(client, organizer, min_age=18)

    assert ids(catalog(client, adult)) == [event["id"]]


def test_age_filter_not_applied_to_own_events(client: TestClient) -> None:
    teen = register(client, OTHER, birth_date="2009-03-01")  # 17 лет
    event = create_event(client, teen, min_age=18)

    assert ids(catalog(client, teen, scope="organized")) == [event["id"]]
    assert ids(catalog(client, teen)) == []


# --- свободные места ---


def test_min_free_places_boundary(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    event = create_event(client, organizer, max_participants=5)
    for index in range(2):
        participant = register(client, f"+7999444{index:04d}")
        client.post(f"/api/events/{event['id']}/join", headers=auth_header(participant))

    two = catalog(client, organizer, min_free_places=2)
    three = catalog(client, organizer, min_free_places=3)

    assert ids(two) == [event["id"]]
    assert two.json()["total"] == 1
    assert ids(three) == []
    assert three.json()["total"] == 0


def test_min_free_places_hides_full(client: TestClient) -> None:
    organizer = register(client, ORGANIZER)
    other = register(client, OTHER)
    full = create_event(client, organizer, max_participants=2)
    client.post(f"/api/events/{full['id']}/join", headers=auth_header(other))
    free = create_event(client, organizer, max_participants=3)

    assert ids(catalog(client, other, min_free_places=1)) == [free["id"]]
    assert ids(catalog(client, organizer, scope="organized", min_free_places=1)) == [free["id"]]


def test_min_free_places_validation(client: TestClient) -> None:
    me = register(client, ORGANIZER)
    for value in (0, 101):
        assert catalog(client, me, min_free_places=value).status_code == 422
