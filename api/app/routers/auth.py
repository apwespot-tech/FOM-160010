from fastapi import APIRouter, Response, status
from pydantic import ValidationError

from app.deps import NowDep, SessionDep, SettingsDep
from app.errors import AppError, not_found
from app.phones import normalize_phone
from app.schemas.auth import (
    CodeRequest,
    CodeRequested,
    RefreshRequest,
    TestCode,
    TokenPair,
    VerifyRequest,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/code")
def request_code(
    body: CodeRequest, session: SessionDep, settings: SettingsDep, now: NowDep
) -> CodeRequested:
    expires_in = auth_service.request_code(session, settings, now, body.phone)
    return CodeRequested(expires_in=expires_in)


@router.get("/test/code", summary="Тестовая ручка: получить действующий код")
def get_test_code(phone: str, session: SessionDep, settings: SettingsDep, now: NowDep) -> TestCode:
    if not settings.auth_test_endpoints:
        raise not_found()
    try:
        normalized = normalize_phone(phone)
    except (ValueError, ValidationError) as exc:
        raise AppError(422, "invalid_phone", "Некорректный номер телефона") from exc
    code = auth_service.get_active_code(session, settings, now, normalized)
    if code is None:
        raise not_found("Действующего кода нет")
    return TestCode(code=code)


@router.post("/verify")
def verify(
    body: VerifyRequest, session: SessionDep, settings: SettingsDep, now: NowDep
) -> TokenPair:
    return auth_service.verify_code(session, settings, now, body.phone, body.code)


@router.post("/refresh")
def refresh(
    body: RefreshRequest, session: SessionDep, settings: SettingsDep, now: NowDep
) -> TokenPair:
    return auth_service.refresh_tokens(session, settings, now, body.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: RefreshRequest, session: SessionDep, now: NowDep) -> Response:
    auth_service.logout(session, now, body.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
