"""Unit-тесты без HTTP: телефоны, токены, схемы профиля."""

import uuid
from contextlib import nullcontext
from datetime import UTC, date, datetime, timedelta

import jwt
import pytest
from pydantic import ValidationError

from app.ages import calculate_age, latest_birth_date
from app.config import Settings
from app.phones import normalize_phone
from app.schemas.event import EventCreate, EventUpdate
from app.schemas.profile import AdminProfileUpdate, ProfileUpdate
from app.security import (
    create_access_token,
    decode_access_token,
    generate_code,
    generate_refresh_token,
    hash_token,
)

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
SETTINGS = Settings(database_url="postgresql+psycopg://unused", jwt_secret="s" * 32)


# --- телефон ---


@pytest.mark.parametrize(
    "raw",
    ["8 (999) 123-45-67", "+7 999 123 45 67", "+79991234567", "89991234567", "9991234567"],
)
def test_phone_normalized_to_e164(raw: str) -> None:
    assert normalize_phone(raw) == "+79991234567"


@pytest.mark.parametrize("raw", ["12ab", "", "123", "+7 999", "+7999123456789"])
def test_invalid_phone_rejected(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_phone(raw)


def test_admin_phones_normalized() -> None:
    settings = Settings(
        database_url="x", jwt_secret="x" * 32, admin_phones="8 999 000-00-01, +79990000002,"
    )
    assert settings.admin_phone_set == {"+79990000001", "+79990000002"}


# --- коды и токены ---


def test_generated_code_is_six_digits() -> None:
    codes = {generate_code() for _ in range(200)}
    assert all(len(code) == 6 and code.isdigit() for code in codes)
    assert len(codes) > 1


def test_refresh_token_is_random_and_hash_is_sha256() -> None:
    token = generate_refresh_token()
    assert token != generate_refresh_token()
    assert len(hash_token(token)) == 64
    assert hash_token(token) != token


def test_access_token_claims_and_lifetime() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id, ["organizer", "participant"], NOW, SETTINGS)

    payload = decode_access_token(token, NOW + timedelta(seconds=899), SETTINGS)
    assert payload["sub"] == str(user_id)
    assert payload["roles"] == ["organizer", "participant"]
    assert payload["type"] == "access"

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token, NOW + timedelta(minutes=15), SETTINGS)


def test_access_token_with_foreign_secret_rejected() -> None:
    other = Settings(database_url="x", jwt_secret="o" * 32)
    token = create_access_token(uuid.uuid4(), [], NOW, other)
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token, NOW, SETTINGS)


# --- профиль ---


@pytest.mark.parametrize(
    ("birth_date", "today", "age"),
    [
        (date(2000, 11, 1), date(2026, 10, 31), 25),
        (date(2000, 10, 31), date(2026, 10, 31), 26),
        (date(2000, 2, 29), date(2026, 2, 28), 25),
        (date(2000, 2, 29), date(2026, 3, 1), 26),
    ],
)
def test_calculate_age(birth_date: date, today: date, age: int) -> None:
    assert calculate_age(birth_date, today) == age


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "   "},
        {"name": "x" * 101},
        {"name": None},
        {"birth_date": None},
        {"telegram": "@abc"},
        {"telegram": "username"},
        {"telegram": "@" + "a" * 33},
        {"email": "not-an-email"},
        {"photo_url": "https://example.com/a.png"},
        {"about": "x" * 501},
        {"interest_ids": [1, 1]},
        {"interest_ids": None},
        {"phone": "+79991234567"},
        {"roles": ["admin"]},
        {"id": str(uuid.uuid4())},
    ],
)
def test_invalid_own_profile_update(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ProfileUpdate.model_validate(payload)


def test_valid_own_profile_update() -> None:
    data = ProfileUpdate.model_validate(
        {
            "name": "  Анна  ",
            "telegram": "@anna_k",
            "email": "ann@example.com",
            "about": "  Люблю настолки\nи прогулки  ",
            "birth_date": "1900-01-01",
        }
    )
    assert data.name == "Анна"
    assert data.about == "Люблю настолки\nи прогулки"
    assert data.model_fields_set == {"name", "telegram", "email", "about", "birth_date"}
    assert ProfileUpdate.model_validate({"about": "   "}).about is None


def test_optional_fields_can_be_cleared() -> None:
    data = ProfileUpdate.model_validate({"telegram": None, "email": None, "about": None})
    assert data.telegram is None and "telegram" in data.model_fields_set


def test_admin_update_accepts_phone_but_not_roles() -> None:
    assert AdminProfileUpdate.model_validate({"phone": "8 999 123 45 67"}).phone == "+79991234567"
    with pytest.raises(ValidationError):
        AdminProfileUpdate.model_validate({"roles": ["admin"]})
    with pytest.raises(ValidationError):
        AdminProfileUpdate.model_validate({"phone": None})
    with pytest.raises(ValidationError):
        AdminProfileUpdate.model_validate({"phone": "12ab"})


# --- схемы мероприятия ---


def _event_fields(**overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        "title": "  Прогулка  ",
        "description": "По набережной",
        "place": "Парк",
        "starts_at": "2026-11-01T19:00:00+03:00",
        "category_id": 2,
        "city_id": 1,
        "max_participants": 5,
        "min_age": 0,
    }
    fields.update(overrides)
    return fields


def test_event_create_strips_strings() -> None:
    event = EventCreate.model_validate(_event_fields())
    assert event.title == "Прогулка"
    assert event.duration_minutes is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": "   "},
        {"title": "x" * 101},
        {"description": "x" * 2001},
        {"place": ""},
        {"starts_at": "2026-11-01T19:00:00"},
        {"duration_minutes": 0},
        {"duration_minutes": 1441},
        {"max_participants": 1},
        {"max_participants": 101},
        {"min_age": 12},
        {"organizer_id": str(uuid.uuid4())},
    ],
)
def test_event_create_rejects_invalid(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        EventCreate.model_validate(_event_fields(**overrides))


@pytest.mark.parametrize(
    "overrides",
    [
        {"max_participants": 2},
        {"max_participants": 100},
        {"min_age": 18},
        {"duration_minutes": 1440},
    ],
)
def test_event_create_accepts_bounds(overrides: dict[str, object]) -> None:
    EventCreate.model_validate(_event_fields(**overrides))


def test_event_update_allows_clearing_only_duration() -> None:
    update = EventUpdate.model_validate({"duration_minutes": None})
    assert update.model_fields_set == {"duration_minutes"}
    with pytest.raises(ValidationError):
        EventUpdate.model_validate({"title": None})
    with pytest.raises(ValidationError):
        EventUpdate.model_validate({"id": str(uuid.uuid4())})


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 11, 5), date(2012, 11, 5)),
        (date(2028, 2, 29), date(2014, 2, 28)),
        (date(2026, 2, 28), date(2012, 2, 28)),
    ],
)
def test_latest_birth_date_for_14(today: date, expected: date) -> None:
    assert latest_birth_date(today, 14) == expected
    assert calculate_age(expected, today) == 14
    assert calculate_age(expected + timedelta(days=1), today) == 13


# --- фоновый процесс ---


def test_worker_run_once_passes_current_time(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import worker

    now = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
    calls: list[datetime] = []

    def fake_create(session: object, at: datetime) -> int:
        calls.append(at)
        return 3

    monkeypatch.setattr(worker.notification_service, "create_review_reminders", fake_create)

    assert worker.run_once(lambda: nullcontext(), lambda: now) == 3  # type: ignore[arg-type]
    assert calls == [now]


def test_worker_run_once_survives_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import worker

    def failing(session: object, at: datetime) -> int:
        raise RuntimeError("таблицы ещё нет")

    monkeypatch.setattr(worker.notification_service, "create_review_reminders", failing)

    now = datetime(2026, 11, 2, tzinfo=UTC)
    assert worker.run_once(lambda: nullcontext(), lambda: now) == 0  # type: ignore[arg-type]


@pytest.mark.parametrize("interval", [0, -5])
def test_worker_interval_must_be_positive(interval: int) -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+psycopg://x",
            jwt_secret="s" * 32,
            worker_interval_seconds=interval,
        )
