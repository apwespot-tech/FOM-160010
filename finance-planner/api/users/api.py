from django.contrib.auth import login, logout
from django.http import HttpRequest
from django.views.decorators.csrf import ensure_csrf_cookie
from ninja import Router, Status
from ninja.decorators import decorate_view
from ninja.utils import check_csrf

from users import services
from users.models import User
from users.schemas import LoginInput, ProfileUpdateInput, RegisterInput, UserOut

router = Router(tags=["Пользователь и вход"])


class CsrfTokenError(Exception):
    pass


def require_csrf_token(request: HttpRequest) -> bool:
    # Регистрация и вход открыты без сессии, а django_auth проверяет токен CSRF только вместе с ней.
    # Проверка стоит на месте auth, чтобы, как у остальных изменяющих маршрутов, идти до разбора тела запроса
    if check_csrf(request) is not None:
        raise CsrfTokenError

    return True


@router.get("/csrf", auth=None, response={204: None}, summary="Выдать куку с токеном CSRF")
@decorate_view(ensure_csrf_cookie)
def issue_csrf_token(request: HttpRequest) -> Status[None]:
    return Status(204, None)


@router.post("/register", auth=require_csrf_token, response={201: UserOut}, summary="Зарегистрировать пользователя и начать сессию")
def register(request: HttpRequest, payload: RegisterInput) -> Status[User]:
    user = services.register_user(payload.username, payload.password, payload.time_zone)
    login(request, user)

    return Status(201, user)


@router.post("/login", auth=require_csrf_token, response={200: UserOut}, summary="Войти")
def log_in(request: HttpRequest, payload: LoginInput) -> User:
    user = services.check_credentials(payload.username, payload.password)
    login(request, user)

    return user


@router.post("/logout", response={204: None}, summary="Выйти")
def log_out(request: HttpRequest) -> Status[None]:
    logout(request)

    return Status(204, None)


@router.get("/me", response={200: UserOut}, summary="Текущий пользователь")
def read_profile(request: HttpRequest) -> User:
    return request.user


@router.patch("/me", response={200: UserOut}, summary="Изменить часовой пояс")
def update_profile(request: HttpRequest, payload: ProfileUpdateInput) -> User:
    return services.update_profile(request.user, payload.time_zone)
