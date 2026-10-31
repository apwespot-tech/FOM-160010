# «Ищу компанию» — совместные активности

Сервис для поиска участников на небольшие события: настольные игры, прогулки, спорт, кино.
Организатор создаёт активность с датой, местом и лимитом участников, остальные находят её в каталоге и записываются.

Подробнее: [описание проекта](docs/project.md).

## Стек

Vue 3 + TypeScript + Vite · Python (FastAPI) · PostgreSQL · Docker Compose.
См. [архитектуру](docs/architecture.md).

## Запуск

Требования: Docker и Docker Compose v2. Сейчас готовы вход, онбординг и профиль.

```bash
cp .env.example .env
docker compose up --build
```

При старте контейнер `api` применяет миграции БД. Frontend (dev-сервер Vite) проксирует `/api` в контейнер `api`, поэтому в браузере всё работает на одном адресе.

| Сервис | Адрес |
|---|---|
| **Сайт** | http://localhost:5173 |
| API | http://localhost:8000/api |
| Документация API (Swagger) | http://localhost:8000/api/docs |
| PostgreSQL | localhost:5432 (логин/пароль из `.env`) |

Остановка (`-v` дополнительно удаляет данные БД):

```bash
docker compose down
```

### Вход в разработке

SMS не отправляются. При `AUTH_TEST_ENDPOINTS=true` сайт показывает код входа прямо на экране ввода кода (оранжевая подсказка «Тестовый режим»). При `false` подсказки нет.

Через API код можно получить тестовой ручкой (работает только при `AUTH_TEST_ENDPOINTS=true`):

1. `POST /api/auth/code` с `{"phone": "+79991234567"}`
2. `GET /api/auth/test/code?phone=%2B79991234567` — вернёт код
3. `POST /api/auth/verify` с телефоном и кодом — вернёт `access_token` и `refresh_token`
4. Передавайте `Authorization: Bearer <access_token>`; сначала заполните профиль через `PATCH /api/profile` (`name`, `birth_date`)

Телефоны администраторов задаются в `ADMIN_PHONES` (через запятую).

Мероприятия пока доступны только через API (frontend появится отдельным изменением): категории — `GET /api/categories`, мероприятия — `/api/events` (каталог, создание, изменение, удаление, `join`, `leave`, список и удаление участников). Все ручки с примерами — в Swagger: http://localhost:8000/api/docs.

## Тесты и проверки

Тесты работают на отдельной БД `app_test` в контейнере `db`:

```bash
docker compose run --rm api pytest
```

Линтер, форматирование и типы:

```bash
docker compose run --rm api sh -c "ruff check . && ruff format --check . && mypy"
```

> БД `app_test` создаётся init-скриптом при первой инициализации тома. Если том `db-data` был создан раньше, пересоздайте его: `docker compose down -v`.

Frontend — тесты (Vitest), линтер, форматирование и типы:

```bash
docker compose run --rm web npm test
```

```bash
docker compose run --rm web sh -c "npm run lint && npm run format:check && npm run typecheck"
```

> `node_modules` фронтенда живут внутри образа `web`. После изменения `web/package.json` пересоберите его: `docker compose build web` (при необходимости с `docker compose up -d --renew-anon-volumes web`).

## Документация

| Документ | Содержание |
|---|---|
| [docs/project.md](docs/project.md) | Назначение, роли, MVP |
| [docs/architecture.md](docs/architecture.md) | Стек, схема, структура репозитория |
| [docs/nfr.md](docs/nfr.md) | Нефункциональные требования |
| [docs/rules.md](docs/rules.md) | Правила разработки |
| [docs/git-workflow.md](docs/git-workflow.md) | Git-процесс курса: ветки и Pull Request |
| [docs/backlog.md](docs/backlog.md) | Доработки на будущее |
| [openspec/specs/](openspec/specs/) | Функциональные требования (OpenSpec) |
