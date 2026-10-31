from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Ошибка бизнес-логики с HTTP-статусом и машинным кодом."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        headers: dict[str, str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers
        self.extra = extra or {}


async def app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": {"code": exc.code, "message": exc.message, **exc.extra}},
        headers=exc.headers,
    )


def unauthorized(message: str = "Требуется авторизация") -> AppError:
    return AppError(401, "invalid_token", message, headers={"WWW-Authenticate": "Bearer"})


def forbidden(message: str = "Недостаточно прав") -> AppError:
    return AppError(403, "forbidden", message)


def not_found(message: str = "Не найдено") -> AppError:
    return AppError(404, "not_found", message)
