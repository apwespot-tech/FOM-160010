# CLAUDE.md

«Ищу компанию» — сервис совместных активностей. Vue 3 + TS + Vite, Python (FastAPI), PostgreSQL, Docker Compose.

## Документация

- [docs/project.md](docs/project.md) — назначение, роли, рамка MVP
- [docs/architecture.md](docs/architecture.md) — стек, схема сервисов, структура репозитория
- [docs/nfr.md](docs/nfr.md) — нефункциональные требования
- [docs/rules.md](docs/rules.md) — правила разработки (код-стайл, слои, тесты, коммиты)
- [docs/git-workflow.md](docs/git-workflow.md) — ветки и PR по правилам курса
- [openspec/specs/](openspec/specs/) — функциональные требования к реализованному поведению
- [openspec/changes/](openspec/changes/) — изменения в работе
- [README.md](README.md) — запуск

## Обязательные правила

- Бизнес-логика добавляется только через OpenSpec: `/opsx:propose` → `/opsx:apply` → `/opsx:archive`.
  Не придумывать бизнес-правила, которых нет в спеках или текущем изменении, — спросить пользователя.
- Авторизация обязательна для всего, кроме регистрации и входа; права проверяются на backend.
- Операции с лимитами — атомарно в одной транзакции.
- Не коммитить в `main`; не коммитить `.env` и секреты.
- Документация и артефакты OpenSpec — на русском.
