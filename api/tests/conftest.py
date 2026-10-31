import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import Settings
from app.main import create_app

API_DIR = Path(__file__).resolve().parents[1]
ADMIN_PHONE = "+79990000001"
TEST_SECRET = "test-secret-" + "x" * 32
START = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)


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
    yield application
    with application.state.engine.begin() as conn:
        conn.execute(
            text("TRUNCATE users, user_roles, auth_codes, refresh_tokens RESTART IDENTITY CASCADE")
        )
    application.state.engine.dispose()


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
    client: TestClient, phone: str, name: str = "Анна", birth_date: str = "2000-01-15"
) -> dict[str, Any]:
    """Вход и заполнение профиля. Возвращает токены и id пользователя."""
    tokens = login(client, phone)
    response = client.patch(
        "/api/profile", json={"name": name, "birth_date": birth_date}, headers=auth_header(tokens)
    )
    assert response.status_code == 200, response.text
    return {**tokens, "id": response.json()["id"]}
