from collections.abc import Callable
from dataclasses import dataclass
from http import HTTPStatus
import os
from pathlib import Path
import re

from django.http import HttpResponse
from django.test import Client
import pytest

from finance_planner.api import api
from users.models import User

JsonSender = Callable[..., HttpResponse]

CONTRACT_PATH_VARIABLE = "API_CONTRACT_PATH"
# Тест лежит в api/finance_planner/tests, а docs рядом с папкой api. В контейнере docs подключена как /docs, и путь тот же
DEFAULT_CONTRACT_PATH = Path(__file__).resolve().parents[3] / "docs" / "api.md"
# Столько маршрутов в таблице раздела 3 docs/api.md, проверка ловит строки, которые разбор таблицы потерял
DOCUMENTED_ROUTE_COUNT = 42
ROUTES_SECTION_HEADING = "## 3. Маршруты"
NEXT_SECTION_PREFIX = "\n## "
HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
UNSAFE_METHODS = ("POST", "PUT", "PATCH", "DELETE")
YES_MARK = "да"
PATH_PARAMETER_PATTERN = re.compile(r"\{[^}]+\}")
SAMPLE_PATH_VALUE = "1"


@dataclass(frozen=True)
class ContractRoute:
    method: str
    path: str
    is_session_required: bool
    success_status: int
    is_ready: bool


@dataclass(frozen=True)
class CodeRoute:
    status_codes: frozenset[int]
    is_session_required: bool


def find_contract_file() -> Path:
    contract_path = Path(os.environ.get(CONTRACT_PATH_VARIABLE, DEFAULT_CONTRACT_PATH))

    if not contract_path.is_file():
        message = f"Нет файла контракта {contract_path}: задайте {CONTRACT_PATH_VARIABLE} или подключите папку docs к контейнеру api"

        raise FileNotFoundError(message)

    return contract_path


def parse_route_cells(cells: list[str]) -> ContractRoute:
    method, path_cell, _purpose, session_cell, success_cell, _errors, _step, ready_cell = cells

    return ContractRoute(
        method=method,
        path=path_cell.strip("`"),
        is_session_required=session_cell == YES_MARK,
        success_status=int(success_cell),
        is_ready=ready_cell == YES_MARK,
    )


def read_contract_routes() -> list[ContractRoute]:
    contract_text = find_contract_file().read_text(encoding="utf-8")
    section_text = contract_text.split(ROUTES_SECTION_HEADING, maxsplit=1)[1]
    table_text = section_text.split(NEXT_SECTION_PREFIX, maxsplit=1)[0]
    routes = []

    for line in table_text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]

        if cells[0] in HTTP_METHODS:
            routes.append(parse_route_cells(cells))

    return routes


def read_code_routes() -> dict[tuple[str, str], CodeRoute]:
    schema = api.get_openapi_schema()
    code_routes = {}

    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            status_codes = frozenset(int(status_code) for status_code in operation["responses"])
            is_session_required = bool(operation.get("security"))
            code_routes[(method.upper(), path)] = CodeRoute(status_codes=status_codes, is_session_required=is_session_required)

    return code_routes


def describe_route(route: ContractRoute) -> str:
    return f"{route.method} {route.path}"


def build_sample_path(route: ContractRoute) -> str:
    return PATH_PARAMETER_PATTERN.sub(SAMPLE_PATH_VALUE, route.path)


def build_sample_body(route: ContractRoute) -> dict[str, object] | None:
    if route.method in UNSAFE_METHODS:
        return {}

    return None


CONTRACT_ROUTES = read_contract_routes()
READY_ROUTES = [route for route in CONTRACT_ROUTES if route.is_ready]
PROTECTED_ROUTES = [route for route in READY_ROUTES if route.is_session_required]
UNSAFE_PROTECTED_ROUTES = [route for route in PROTECTED_ROUTES if route.method in UNSAFE_METHODS]


def test_contract_table_is_read() -> None:
    assert len(CONTRACT_ROUTES) == DOCUMENTED_ROUTE_COUNT
    assert READY_ROUTES


def test_ready_routes_exist_in_code() -> None:
    code_routes = read_code_routes()
    missing_routes = []

    for route in READY_ROUTES:
        code_route = code_routes.get((route.method, route.path))

        if code_route is None or route.success_status not in code_route.status_codes:
            missing_routes.append(f"{describe_route(route)} {route.success_status}")

    assert missing_routes == []


def test_code_routes_are_ready_in_contract() -> None:
    ready_keys = {(route.method, route.path) for route in READY_ROUTES}
    unlisted_routes = [f"{method} {path}" for method, path in read_code_routes() if (method, path) not in ready_keys]

    assert unlisted_routes == []


def test_session_requirement_matches_contract() -> None:
    code_routes = read_code_routes()
    mismatched_routes = []

    for route in READY_ROUTES:
        code_route = code_routes.get((route.method, route.path))

        if code_route is not None and code_route.is_session_required != route.is_session_required:
            mismatched_routes.append(describe_route(route))

    assert mismatched_routes == []


@pytest.mark.django_db
@pytest.mark.parametrize("route", PROTECTED_ROUTES, ids=describe_route)
def test_protected_route_requires_session(route: ContractRoute, send_json: JsonSender) -> None:
    response = send_json(route.method, build_sample_path(route), build_sample_body(route))

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["code"] == "not_authenticated"


@pytest.mark.django_db
@pytest.mark.usefixtures("csrf_token")
@pytest.mark.parametrize("route", UNSAFE_PROTECTED_ROUTES, ids=describe_route)
def test_unsafe_route_requires_csrf_token(route: ContractRoute, send_json: JsonSender, csrf_client: Client, user: User) -> None:
    csrf_client.force_login(user)
    response = send_json(route.method, build_sample_path(route), build_sample_body(route), should_send_token=False)

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json()["code"] == "csrf_failed"
