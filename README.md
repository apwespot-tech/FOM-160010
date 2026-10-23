# FOM-160010 · Y.Novikova

Рабочее окружение для индивидуального проекта курса «Веб-разработка».
Правила работы с ветками общего репозитория описаны в README ветки `main`.

| Ветка | Назначение |
|---|---|
| `Y.Novikova/main` | личная стабильная ветка |
| `Y.Novikova/work-branch` | рабочая ветка задачи, сдаётся через PR в `Y.Novikova/main` |

## Структура

```text
FOM-160010/
├── web/            # Vue 3 + TypeScript (Vite)
├── api/            # PHP 8.3 / Laravel, маршрут /health
├── compose.yaml    # PostgreSQL, Laravel API и Vue
├── .env.example    # образец переменных
├── .gitignore      # секреты и зависимости не попадают в Git
└── README.md       # запуск и проверки
```

| Сервис | Адрес | Что это |
|---|---|---|
| `web` | http://localhost:5173 | Vue через Vite, запросы `/health` проксируются в API |
| `api` | http://localhost:8000 | Laravel API |
| `db` | `db:5432` внутри сети Docker | PostgreSQL 17, данные в томе `pgdata` |

На компьютере нужны только Git и Docker Desktop: PHP, Composer и Node.js работают в контейнерах.

## Запуск

```bash
# один раз: локальный файл секретов (в Git не попадает)
cp .env.example .env          # Windows PowerShell: copy .env.example .env

# собрать и запустить все сервисы
docker compose up -d --build
```

Первый запуск занимает несколько минут: Docker скачивает образы, Composer и npm ставят зависимости.
При старте контейнер `api` сам создаёт `api/.env` из образца, генерирует `APP_KEY` и применяет миграции.

## Проверка готовности (слайд 25)

```bash
docker compose ps                                   # контейнеры db, api, web запущены
docker compose exec db pg_isready -U urfu -d urfu   # accepting connections
curl -i http://127.0.0.1:8000/health                # 200 OK, {"status":"ok","database":"ok"}
```

Страница http://localhost:5173 показывает три зелёные точки: Vue, Laravel API и PostgreSQL.

| Часть | Признак готовности |
|---|---|
| GitHub | `Y.Novikova/main`, `Y.Novikova/work-branch` и PR |
| Vue | страница открывается |
| PHP / Laravel | `GET /health` → 200 |
| Docker | контейнеры видны в `docker compose ps` |
| PostgreSQL | `pg_isready` подтверждает готовность |

## Повседневные команды

| Команда | Зачем |
|---|---|
| `docker compose up -d --build` | собрать и запустить |
| `docker compose ps` | что запущено |
| `docker compose logs -f api` | логи API |
| `docker compose down` | остановить |

`docker compose down -v` удаляет ещё и том с базой — не использовать без необходимости.

## Если не работает

| Симптом | Что проверить |
|---|---|
| Docker не отвечает | `docker info`, запущен ли Docker Desktop |
| Порт занят | `docker compose ps`, `netstat -ano \| findstr :8000` |
| API не отвечает | `docker compose logs api` |
| База недоступна | внутри Docker хост базы — `db`, а не `localhost` |
