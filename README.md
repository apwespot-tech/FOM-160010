# «Ищу компанию» — совместные активности

Сервис для поиска участников на небольшие события: настольные игры, прогулки, спорт, кино.
Организатор создаёт активность с датой, местом и лимитом участников, остальные находят её в каталоге и записываются.

Подробнее: [описание проекта](docs/project.md).

## Стек

Vue 3 + TypeScript + Vite · Python (FastAPI) · PostgreSQL · Docker Compose.
См. [архитектуру](docs/architecture.md).

## Запуск

Требования: Docker и Docker Compose v2. Сейчас реализован только backend.

```bash
cp .env.example .env
docker compose up --build
```

При старте контейнер `api` применяет миграции БД.

| Сервис | Адрес |
|---|---|
| API | http://localhost:8000/api |
| Документация API (Swagger) | http://localhost:8000/api/docs |
| PostgreSQL | localhost:5432 (логин/пароль из `.env`) |

Остановка (`-v` дополнительно удаляет данные БД):

```bash
docker compose down
```

### Вход в разработке

SMS не отправляются. Код входа можно получить тестовой ручкой, которая работает только при `AUTH_TEST_ENDPOINTS=true`:

1. `POST /api/auth/code` с `{"phone": "+79991234567"}`
2. `GET /api/auth/test/code?phone=%2B79991234567` — вернёт код
3. `POST /api/auth/verify` с телефоном и кодом — вернёт `access_token` и `refresh_token`
4. Передавайте `Authorization: Bearer <access_token>`; сначала заполните профиль через `PATCH /api/profile` (`name`, `birth_date`)

Телефоны администраторов задаются в `ADMIN_PHONES` (через запятую).

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

## Документация

| Документ | Содержание |
|---|---|
| [docs/project.md](docs/project.md) | Назначение, роли, MVP |
| [docs/architecture.md](docs/architecture.md) | Стек, схема, структура репозитория |
| [docs/nfr.md](docs/nfr.md) | Нефункциональные требования |
| [docs/rules.md](docs/rules.md) | Правила разработки |
| [docs/git-workflow.md](docs/git-workflow.md) | Git-процесс курса: ветки и Pull Request |
| [openspec/specs/](openspec/specs/) | Функциональные требования (OpenSpec) |
