import os
import uuid
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Row, delete, text
from sqlalchemy.orm import Session

from app.config import Settings
from app.main import create_app
from app.models import Role, UserRole

API_DIR = Path(__file__).resolve().parents[1]
ADMIN_PHONE = "+79990000001"
TEST_SECRET = "test-secret-" + "x" * 32
START = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
# Москва — первый город справочника (миграция 0005)
MOSCOW_ID = 1


class FakeClock:
    """Управляемые часы приложения."""

    def __init__(self, start: datetime) -> None:
        self.current = start

    def __call__(self) -> datetime:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += timedelta(seconds=seconds)


def alembic_config(url: str) -> Config:
    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    config.attributes["configure_logger"] = False
    return config


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.exit("Не задан TEST_DATABASE_URL", returncode=2)
    return url


@pytest.fixture(scope="session")
def migrated_db(database_url: str) -> str:
    config = alembic_config(database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    return database_url


@pytest.fixture
def settings(migrated_db: str) -> Settings:
    return Settings(
        database_url=migrated_db,
        jwt_secret=TEST_SECRET,
        auth_test_endpoints=True,
        admin_phones=ADMIN_PHONE,
    )


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(START)


@pytest.fixture
def app(settings: Settings, clock: FakeClock) -> Iterator[FastAPI]:
    application = create_app(settings)
    application.state.clock = clock
    # Справочники заполнены миграциями: запоминаем их, чтобы вернуть после правок администратора
    with application.state.engine.connect() as conn:
        seed_categories = conn.execute(text("SELECT id, name, icon FROM categories")).all()
        seed_cities = conn.execute(text("SELECT id, name FROM cities")).all()
    yield application
    with application.state.engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE notifications, reviews, event_photo_data, event_photos, "
                "event_participants, events, user_interests, user_images, users, user_roles, "
                "auth_codes, refresh_tokens "
                "RESTART IDENTITY CASCADE"
            )
        )
        restore_dictionaries(conn, seed_categories, seed_cities)
    application.state.engine.dispose()


def restore_dictionaries(
    conn: Connection, categories: Sequence[Row], cities: Sequence[Row]
) -> None:
    """Удаляет созданные в тесте категории и города и возвращает названия засеянным."""
    conn.execute(
        text("DELETE FROM categories WHERE id <> ALL(:ids)"), {"ids": [c.id for c in categories]}
    )
    conn.execute(text("DELETE FROM cities WHERE id <> ALL(:ids)"), {"ids": [c.id for c in cities]})
    # Временные названия снимают конфликты уникальности при обмене именами
    conn.execute(text("UPDATE categories SET name = '~' || id"))
    conn.execute(text("UPDATE cities SET name = '~' || id"))
    for row in categories:
        conn.execute(
            text("UPDATE categories SET name = :name, icon = :icon WHERE id = :id"),
            {"id": row.id, "name": row.name, "icon": row.icon},
        )
    for row in cities:
        conn.execute(
            text("UPDATE cities SET name = :name WHERE id = :id"), {"id": row.id, "name": row.name}
        )
    conn.execute(
        text("DELETE FROM category_covers WHERE id NOT IN (SELECT cover_id FROM categories)")
    )


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture
def db(app: FastAPI) -> Iterator[Session]:
    with app.state.session_factory() as session:
        yield session


# --- хелперы ---


def get_code(client: TestClient, phone: str) -> str:
    response = client.get("/api/auth/test/code", params={"phone": phone})
    assert response.status_code == 200, response.text
    code: str = response.json()["code"]
    return code


def login(client: TestClient, phone: str) -> dict[str, Any]:
    assert client.post("/api/auth/code", json={"phone": phone}).status_code == 200
    response = client.post(
        "/api/auth/verify", json={"phone": phone, "code": get_code(client, phone)}
    )
    assert response.status_code == 200, response.text
    tokens: dict[str, Any] = response.json()
    return tokens


def auth_header(tokens: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def register(
    client: TestClient,
    phone: str,
    name: str = "Анна",
    birth_date: str = "2000-01-15",
    **profile: Any,
) -> dict[str, Any]:
    """Вход и заполнение профиля (доп. поля — telegram, email...). Возвращает токены и id."""
    tokens = login(client, phone)
    response = client.patch(
        "/api/profile",
        json={"name": name, "birth_date": birth_date, **profile},
        headers=auth_header(tokens),
    )
    assert response.status_code == 200, response.text
    return {**tokens, "id": response.json()["id"]}


def event_payload(**overrides: Any) -> dict[str, Any]:
    """Корректное мероприятие на завтра; поля можно переопределить."""
    payload: dict[str, Any] = {
        "title": "Настолки в антикафе",
        "description": "Играем в «Каркассон» и «Кодовые имена»",
        "place": "Антикафе «Циферблат»",
        "starts_at": (START + timedelta(days=1)).isoformat(),
        "category_id": 1,
        "city_id": MOSCOW_ID,
        "max_participants": 5,
        "min_age": 0,
    }
    payload.update(overrides)
    return payload


def create_event(client: TestClient, user: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    response = client.post(
        "/api/events", json=event_payload(**overrides), headers=auth_header(user)
    )
    assert response.status_code == 201, response.text
    event: dict[str, Any] = response.json()
    return event


def join(client: TestClient, user: dict[str, Any], event_id: str) -> Any:
    return client.post(f"/api/events/{event_id}/join", headers=auth_header(user))


def set_roles(db: Session, user_id: str, roles: list[Role]) -> None:
    db.execute(delete(UserRole).where(UserRole.user_id == uuid.UUID(user_id)))
    db.add_all(UserRole(user_id=uuid.UUID(user_id), role=role) for role in roles)
    db.commit()


def upload_avatar(client: TestClient, user: dict[str, Any], content: bytes | None = None) -> str:
    """Загружает аватар (по умолчанию — маленький JPEG) и возвращает avatar_id."""
    from tests.images import make_image

    response = client.put(
        "/api/profile/avatar",
        files={"file": ("me.jpg", content or make_image("JPEG"), "image/jpeg")},
        headers=auth_header(user),
    )
    assert response.status_code == 200, response.text
    avatar_id: str = response.json()["avatar_id"]
    return avatar_id
