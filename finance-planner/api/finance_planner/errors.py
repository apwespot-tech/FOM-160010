from functools import partial
from http import HTTPStatus
import logging

from django.core.exceptions import BadRequest, SuspiciousOperation
from django.http import Http404, HttpRequest, HttpResponse, RawPostDataException, UnreadablePostError
from django.http.multipartparser import MultiPartParserError
from ninja import NinjaAPI
from ninja.errors import AuthenticationError, HttpError, Throttled, ValidationError

from ledger.services import AccountInUseError, CategoryInUseError, CommonCategoryError, LedgerRuleError, TransferOperationError
from users.api import CsrfTokenError
from users.services import InvalidCredentialsError, UserRuleError

logger = logging.getLogger(__name__)

# Этим текстом django_auth в Ninja 1.7 сообщает об отказе проверки CSRF, другого признака у такой ошибки нет
NINJA_CSRF_FAILURE_TEXT = "CSRF check Failed"

ERROR_DETAILS = {
    "bad_request": "Тело запроса не разбирается как JSON",
    "not_authenticated": "Требуется вход",
    "invalid_credentials": "Неверный логин или пароль",
    "csrf_failed": "Нет токена CSRF или он устарел",
    "common_category": "Общую категорию нельзя изменить или удалить",
    "not_found": "Объект не найден",
    "account_in_use": "Счёт нельзя удалить: на него ссылаются операции. Его можно перенести в архив",
    "category_in_use": "Категорию нельзя удалить: на неё ссылаются операции",
    "transfer_operation": "Операция входит в перевод и меняется только вместе с ним",
    "too_many_requests": "Слишком много запросов. Повторите позже",
    "internal_error": "Внутренняя ошибка сервера",
}

FIXED_ERRORS = {
    AccountInUseError: (HTTPStatus.CONFLICT, "account_in_use"),
    AuthenticationError: (HTTPStatus.UNAUTHORIZED, "not_authenticated"),
    CategoryInUseError: (HTTPStatus.CONFLICT, "category_in_use"),
    CommonCategoryError: (HTTPStatus.FORBIDDEN, "common_category"),
    CsrfTokenError: (HTTPStatus.FORBIDDEN, "csrf_failed"),
    Http404: (HTTPStatus.NOT_FOUND, "not_found"),
    InvalidCredentialsError: (HTTPStatus.UNAUTHORIZED, "invalid_credentials"),
    Throttled: (HTTPStatus.TOO_MANY_REQUESTS, "too_many_requests"),
    TransferOperationError: (HTTPStatus.CONFLICT, "transfer_operation"),
    # Так Django сообщает о теле, которое нельзя прочитать: испорченная форма, уже прочитанная форма, оборванная отправка
    BadRequest: (HTTPStatus.BAD_REQUEST, "bad_request"),
    MultiPartParserError: (HTTPStatus.BAD_REQUEST, "bad_request"),
    RawPostDataException: (HTTPStatus.BAD_REQUEST, "bad_request"),
    UnreadablePostError: (HTTPStatus.BAD_REQUEST, "bad_request"),
}


def build_error_response(request: HttpRequest, api: NinjaAPI, status: HTTPStatus, code: str) -> HttpResponse:
    body = {"code": code, "detail": ERROR_DETAILS[code]}

    return api.create_response(request, body, status=status)


def handle_fixed_error(request: HttpRequest, error: Exception, api: NinjaAPI, status: HTTPStatus, code: str) -> HttpResponse:
    return build_error_response(request, api, status, code)


def handle_http_error(request: HttpRequest, error: HttpError, api: NinjaAPI) -> HttpResponse:
    is_csrf_failure = error.status_code == HTTPStatus.FORBIDDEN and error.message == NINJA_CSRF_FAILURE_TEXT

    if is_csrf_failure:
        return build_error_response(request, api, HTTPStatus.FORBIDDEN, "csrf_failed")

    # Других ошибок HttpError с кодом 400 в Ninja 1.7 нет: так он отвечает на тело, которое не разбирается как JSON
    if error.status_code == HTTPStatus.BAD_REQUEST:
        return build_error_response(request, api, HTTPStatus.BAD_REQUEST, "bad_request")

    return handle_unexpected_error(request, error, api)


def handle_suspicious_operation(request: HttpRequest, error: SuspiciousOperation, api: NinjaAPI) -> HttpResponse:
    # Как сам Django: подозрительный запрос, например тело больше DATA_UPLOAD_MAX_MEMORY_SIZE, пишется в журнал django.security
    error_class_name = type(error).__name__
    security_logger = logging.getLogger(f"django.security.{error_class_name}")
    security_logger.error(str(error), exc_info=error, extra={"status_code": HTTPStatus.BAD_REQUEST, "request": request})

    return build_error_response(request, api, HTTPStatus.BAD_REQUEST, "bad_request")


def handle_validation_error(request: HttpRequest, error: ValidationError, api: NinjaAPI) -> HttpResponse:
    body = {"code": "validation_error", "detail": error.errors}

    return api.create_response(request, body, status=HTTPStatus.UNPROCESSABLE_CONTENT)


def build_rule_error(field_name: str, message: str) -> dict[str, object]:
    return {"type": "planner_rule", "loc": ["body", "payload", field_name], "msg": message}


def handle_rule_error(request: HttpRequest, error: UserRuleError | LedgerRuleError, api: NinjaAPI) -> HttpResponse:
    field_errors = [build_rule_error(field_name, message) for field_name, message in error.field_errors]

    return handle_validation_error(request, ValidationError(field_errors), api)


def handle_unexpected_error(request: HttpRequest, error: Exception, api: NinjaAPI) -> HttpResponse:
    logger.error("Необработанная ошибка в запросе %s %s", request.method, request.path, exc_info=error)

    return build_error_response(request, api, HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error")


def register_error_handlers(api: NinjaAPI) -> None:
    for exception_class, (status, code) in FIXED_ERRORS.items():
        fixed_handler = partial(handle_fixed_error, api=api, status=status, code=code)
        api.add_exception_handler(exception_class, fixed_handler)

    api.add_exception_handler(HttpError, partial(handle_http_error, api=api))
    api.add_exception_handler(SuspiciousOperation, partial(handle_suspicious_operation, api=api))
    api.add_exception_handler(ValidationError, partial(handle_validation_error, api=api))
    api.add_exception_handler(UserRuleError, partial(handle_rule_error, api=api))
    api.add_exception_handler(LedgerRuleError, partial(handle_rule_error, api=api))
    api.add_exception_handler(Exception, partial(handle_unexpected_error, api=api))
