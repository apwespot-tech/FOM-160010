"""Фоновый процесс: раз в `WORKER_INTERVAL_SECONDS` создаёт напоминания об окне отзывов.

Запуск: `python -m app.worker` (сервис `worker` в compose). Ошибка одного прогона
логируется и не останавливает цикл — так переживается и старт раньше миграций.
"""

import logging
import signal
import threading
from types import FrameType

from sqlalchemy.orm import Session, sessionmaker

from app.clock import Clock, utc_now
from app.config import Settings
from app.db import make_engine, make_session_factory
from app.services import notification_service

logger = logging.getLogger("app.worker")


def run_once(session_factory: sessionmaker[Session], clock: Clock) -> int:
    """Один прогон. Возвращает число созданных напоминаний, при ошибке — 0."""
    try:
        with session_factory() as session:
            created = notification_service.create_review_reminders(session, clock())
    except Exception:
        logger.exception("Прогон фонового процесса завершился ошибкой")
        return 0
    logger.info("Создано напоминаний об отзывах: %d", created)
    return created


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = Settings()
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    stop = threading.Event()

    def handle_stop(signum: int, _: FrameType | None) -> None:
        logger.info("Получен сигнал %d, завершение", signum)
        stop.set()

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)

    logger.info("Фоновый процесс запущен, интервал %d с", settings.worker_interval_seconds)
    while not stop.is_set():
        run_once(session_factory, utc_now)
        stop.wait(settings.worker_interval_seconds)
    engine.dispose()


if __name__ == "__main__":
    main()
