from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.phones import normalize_phone


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения."""

    model_config = SettingsConfigDict(extra="ignore")

    database_url: str
    # Не короче 32 байт: рекомендация RFC 7518 для HS256
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"

    access_token_ttl_seconds: int = 15 * 60
    refresh_token_ttl_seconds: int = 30 * 24 * 60 * 60

    auth_code_ttl_seconds: int = 5 * 60
    auth_code_cooldown_seconds: int = 60
    auth_code_max_attempts: int = 5

    auth_test_endpoints: bool = False
    # Телефоны администраторов через запятую
    admin_phones: str = ""

    @property
    def admin_phone_set(self) -> frozenset[str]:
        return frozenset(
            normalize_phone(raw) for raw in self.admin_phones.split(",") if raw.strip()
        )
