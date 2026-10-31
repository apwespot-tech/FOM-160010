# «Ищу компанию» — совместные активности

Сервис для поиска участников на небольшие события: настольные игры, прогулки, спорт, кино.
Организатор создаёт активность с датой, местом и лимитом участников, остальные находят её в каталоге и записываются.

Подробнее: [описание проекта](docs/project.md).

## Стек

Vue 3 + TypeScript + Vite · Python (FastAPI) · PostgreSQL · Docker Compose.
См. [архитектуру](docs/architecture.md).

## Запуск

> Код приложения ещё не добавлен — команды ниже описывают целевой способ запуска и будут уточнены вместе с `compose.yaml`.

Требования: Docker и Docker Compose v2.

```bash
cp .env.example .env
docker compose up --build
```

После запуска:

| Сервис | Адрес |
|---|---|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000/api |
| Документация API | http://localhost:8000/docs |

Остановка:

```bash
docker compose down
```

## Документация

| Документ | Содержание |
|---|---|
| [docs/project.md](docs/project.md) | Назначение, роли, MVP |
| [docs/architecture.md](docs/architecture.md) | Стек, схема, структура репозитория |
| [docs/nfr.md](docs/nfr.md) | Нефункциональные требования |
| [docs/rules.md](docs/rules.md) | Правила разработки |
| [docs/git-workflow.md](docs/git-workflow.md) | Git-процесс курса: ветки и Pull Request |
| [openspec/specs/](openspec/specs/) | Функциональные требования (OpenSpec) |
