import logging

from fastapi import FastAPI

from app.clock import utc_now
from app.config import Settings
from app.db import make_engine, make_session_factory
from app.errors import AppError, app_error_handler
from app.routers import auth, categories, events, profile

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    engine = make_engine(settings.database_url)

    app = FastAPI(
        title="Ищу компанию — API",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.clock = utc_now

    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(auth.router, prefix="/api")
    app.include_router(profile.router, prefix="/api")
    app.include_router(categories.router, prefix="/api")
    app.include_router(events.router, prefix="/api")

    if settings.auth_test_endpoints:
        logger.warning(
            "AUTH_TEST_ENDPOINTS включён: GET /api/auth/test/code раскрывает коды входа. "
            "Не используйте это в рабочем окружении."
        )
    return app
