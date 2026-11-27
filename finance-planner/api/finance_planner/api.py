import platform
import time

import django
from django.db import connection
from django.db.utils import DatabaseError
from django.http import HttpRequest
from ninja import NinjaAPI, Schema, Status
from ninja.security import django_auth

from finance_planner.errors import register_error_handlers
from ledger.api import accounts_router, categories_router, operations_router
from users.api import router as users_router


class DatabaseHealth(Schema):
    status: str
    version: str | None = None
    query_time_ms: float | None = None


class ServiceHealth(Schema):
    status: str
    python_version: str
    django_version: str
    database: DatabaseHealth


api = NinjaAPI(title="API финансового планера", version="0.1.0", auth=django_auth)
register_error_handlers(api)
api.add_router("/auth", users_router)
api.add_router("/accounts", accounts_router)
api.add_router("/categories", categories_router)
api.add_router("/operations", operations_router)


def measure_database() -> DatabaseHealth:
    started_at = time.perf_counter()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW server_version")
            row = cursor.fetchone()
    except DatabaseError:
        return DatabaseHealth(status="unavailable")

    elapsed_ms = (time.perf_counter() - started_at) * 1000
    raw_version = str(row[0])
    server_version = raw_version.split(" ")[0]

    return DatabaseHealth(status="ok", version=server_version, query_time_ms=round(elapsed_ms, 1))


@api.get("/health", auth=None, response={200: ServiceHealth, 503: ServiceHealth}, summary="Состояние API и базы")
def health(request: HttpRequest) -> Status[ServiceHealth]:
    database_health = measure_database()
    service_status = "ok"
    status_code = 200

    if database_health.status != "ok":
        service_status = "degraded"
        status_code = 503

    payload = ServiceHealth(
        status=service_status,
        python_version=platform.python_version(),
        django_version=django.get_version(),
        database=database_health,
    )

    return Status(status_code, payload)
