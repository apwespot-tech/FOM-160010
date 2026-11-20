from django.contrib.sessions.backends.base import VALID_KEY_CHARS
from django.contrib.sessions.backends.db import SessionStore as DatabaseSessionStore

SESSION_KEY_CHARACTERS = frozenset(VALID_KEY_CHARS)


class SessionStore(DatabaseSessionStore):
    # Django выдаёт ключи сессий из строчных латинских букв и цифр, а у ключа из куки проверяет только длину.
    # Ключ с другими знаками, например с NUL, дошёл бы до запроса к PostgreSQL и дал бы ошибку 500
    def _validate_session_key(self, key: str | None) -> bool:
        has_valid_length = bool(super()._validate_session_key(key))

        return has_valid_length and set(key) <= SESSION_KEY_CHARACTERS
