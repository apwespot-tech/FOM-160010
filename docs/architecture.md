# Архитектура и стек

## Стек

| Слой | Технологии |
|---|---|
| Frontend | Vue 3, TypeScript, Vite |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (sync, psycopg 3), Alembic, PyJWT |
| База данных | PostgreSQL 16 |
| Тесты | pytest (backend), Vitest (frontend) |
| Запуск | Docker Compose |

## Схема

```text
 браузер
    |
    v
 +--------------+   HTTP/JSON   +--------------+   SQL   +--------------+
 | web          | ------------> | api          | ------> | db           |
 | Vue 3 + Vite |    /api/*     | FastAPI      |         | PostgreSQL   |
 +--------------+               +--------------+         +--------------+
        \__________________ docker compose __________________/
```

- `web` — SPA. Обращается к backend по префиксу `/api`.
- `api` — REST API. Вся бизнес-логика и проверки (включая лимиты) выполняются здесь, не на клиенте.
- `db` — единственное хранилище состояния. Схема меняется только миграциями Alembic.

## Структура репозитория

```text
.
├── api/                    # backend (FastAPI)
│   ├── app/
│   │   ├── main.py         # create_app(): приложение, роутеры под /api
│   │   ├── config.py       # Settings из переменных окружения
│   │   ├── db.py           # engine и фабрика сессий
│   │   ├── clock.py        # текущее время (подменяется в тестах)
│   │   ├── errors.py       # AppError → {"detail": {"code", "message"}}
│   │   ├── security.py     # JWT, коды, refresh-токены
│   │   ├── phones.py       # нормализация телефона в E.164
│   │   ├── deps.py         # зависимости: сессия, текущий пользователь, права
│   │   ├── models/         # SQLAlchemy-модели
│   │   ├── schemas/        # Pydantic-схемы запросов и ответов
│   │   ├── services/       # бизнес-логика
│   │   └── routers/        # HTTP-слой
│   ├── migrations/         # Alembic
│   ├── docker/initdb/      # init-скрипты PostgreSQL (БД app_test)
│   ├── tests/
│   ├── Dockerfile
│   └── pyproject.toml
├── web/                    # frontend (Vue 3 + Vite) — ещё не создан
├── docs/                   # документация проекта
├── openspec/               # спеки и изменения OpenSpec
├── compose.yaml
├── .env.example
└── README.md
```

При изменении структуры обновите этот раздел.

## Backend: ключевые решения

- Слои: `routers` → `services` → `models`. Роутеры не работают с БД напрямую.
- Время берётся из `app.state.clock`, а не из `datetime.now()`, чтобы тесты управляли временем.
- Операции, чувствительные к гонкам, сериализуются средствами PostgreSQL: advisory-лок по номеру телефона, атомарный `UPDATE ... RETURNING`, уникальные индексы.
- Тесты работают на реальном PostgreSQL (БД `app_test`): миграции применяются один раз за сессию, таблицы очищаются между тестами.
