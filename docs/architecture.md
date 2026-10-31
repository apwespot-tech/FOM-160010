# Архитектура и стек

## Стек

| Слой | Технологии |
|---|---|
| Frontend | Vue 3, TypeScript (strict), Vite, vue-router, Pinia, PrimeVue 4.5 (MIT), primeicons 7 |
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

- `web` — SPA. Обращается к backend по префиксу `/api`. В разработке dev-сервер Vite (порт 5173) проксирует `/api` на `VITE_API_PROXY_TARGET` (`http://api:8000` в compose), поэтому браузер видит один origin и CORS не нужен.
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
├── web/                    # frontend (Vue 3 + Vite)
│   ├── src/
│   │   ├── main.ts         # приложение: Pinia, роутер, PrimeVue (тема, локаль ru)
│   │   ├── App.vue         # шапка и RouterView
│   │   ├── theme.ts        # пресет PrimeVue: фиолетовый primary, задел под тёмную тему
│   │   ├── styles.css      # брейкпоинты, переменные --app-*, базовая раскладка
│   │   ├── api/            # fetch-клиент (ApiError, single-flight refresh), auth, profile
│   │   ├── stores/         # Pinia: session (токены, профиль)
│   │   ├── router/         # маршруты и гард доступа
│   │   ├── composables/    # useCountdown
│   │   ├── utils/          # даты, форматирование, брейкпоинты
│   │   ├── components/     # PhoneStep, CodeStep, DevCodeHint, ProfileForm, ProfileCard
│   │   └── views/          # LoginView, OnboardingView, ProfileView
│   ├── tests/              # Vitest + Vue Test Utils (jsdom)
│   ├── Dockerfile
│   └── package.json
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

## Frontend: ключевые решения

- Сессия: access-токен только в памяти, refresh-токен в `localStorage` (`ik.refreshToken`). При загрузке страницы сессия восстанавливается через `POST /auth/refresh`.
- При 401 клиент один раз обновляет токены и повторяет запрос. Обновление single-flight: одновременные запросы ждут один и тот же промис, потому что backend ротирует refresh-токен.
- Гард маршрутов: гость → `/login`, незаполненный профиль → `/onboarding`, заполненный → `/profile`. Страницы грузятся лениво.
- Подсказка с тестовым кодом (`DevCodeHint`) — временный костыль до SMS. Она показывается, только если `GET /api/auth/test/code` ответил 200. Удаляется вместе с `getTestCode`.
- Адаптивность mobile-first, правила — в [rules.md](rules.md#ui).
