# Архитектура и стек

## Стек

| Слой | Технологии |
|---|---|
| Frontend | Vue 3, TypeScript, Vite |
| Backend | Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2, Alembic |
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

## Структура репозитория (план)

```text
.
├── api/              # backend (FastAPI)
│   ├── app/
│   ├── migrations/   # Alembic
│   └── tests/
├── web/              # frontend (Vue 3 + Vite)
│   └── src/
├── docs/             # документация проекта
├── openspec/         # спеки и изменения OpenSpec
├── compose.yaml
├── .env.example
└── README.md
```

Структура уточняется по мере появления кода; при изменении обновите этот раздел.
