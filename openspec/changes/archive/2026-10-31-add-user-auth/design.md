# Design

## Context

Кода в репозитории нет: это изменение создаёт backend с нуля. Стек и правила заданы в `docs/architecture.md`, `docs/nfr.md` и `docs/rules.md`. Мотивация — в proposal.md, требования — в `specs/auth` и `specs/user-profile`.

## Goals / Non-Goals

**Goals:**
- Каркас `api/`, на котором будут строиться следующие порции: слои, конфигурация, миграции, тестовая инфраструктура.
- Корректность при конкурентных запросах (коды, refresh-токены, уникальность) средствами PostgreSQL.
- Детерминированные тесты времени: срок кода, интервал повторного запроса, срок токенов, возраст.

**Non-Goals:**
- Отправка SMS, rate limiting по IP, защита от перебора номеров.
- Мгновенный отзыв access-токенов (живут до истечения 15 минут).
- Frontend и CORS-настройки под него.

## Decisions

### Стек backend
Python 3.12, FastAPI, Pydantic v2 и pydantic-settings, SQLAlchemy 2 в синхронном режиме с драйвером psycopg 3, Alembic, PyJWT, `phonenumbers`, `email-validator`. Тесты — pytest и `TestClient`. Качество — ruff и mypy. Зависимости описаны в `api/pyproject.toml`.

Синхронный SQLAlchemy выбран вместо async: FastAPI выполняет синхронные обработчики в пуле потоков, нагрузка учебная, а код и тесты (в том числе конкурентные, на потоках) получаются проще. При необходимости переход на async локализован в слое доступа к данным.

### Структура `api/`

```text
api/
├── app/
│   ├── main.py          # создание приложения, подключение роутеров под /api
│   ├── config.py        # Settings из переменных окружения
│   ├── db.py            # engine, фабрика сессий, зависимость get_session
│   ├── clock.py         # зависимость now(), подменяется в тестах
│   ├── errors.py        # AppError и обработчик: {"detail": {"code", "message"}}
│   ├── security.py      # JWT, генерация кода и refresh-токена, хеширование
│   ├── deps.py          # current_user, require_completed_profile, require_admin
│   ├── models/          # SQLAlchemy-модели
│   ├── schemas/         # Pydantic-схемы запросов и ответов
│   ├── services/        # auth_service, profile_service — бизнес-логика
│   └── routers/         # auth.py, profile.py — только HTTP
├── migrations/          # Alembic
├── tests/
├── Dockerfile
├── alembic.ini
└── pyproject.toml
```

Роутеры не обращаются к БД напрямую, вся логика — в сервисах (`docs/rules.md`).

### Схема БД (миграция `0001_users_auth`)

```text
users
  id           uuid PK DEFAULT gen_random_uuid()
  phone        text NOT NULL UNIQUE           -- E.164
  name         text NULL
  birth_date   date NULL
  email        text NULL                      -- UNIQUE INDEX on lower(email)
  telegram     text NULL
  photo_url    text NULL
  created_at   timestamptz NOT NULL DEFAULT now()
  updated_at   timestamptz NOT NULL DEFAULT now()

user_roles
  user_id      uuid FK -> users(id) ON DELETE CASCADE
  role         user_role NOT NULL             -- enum: participant, organizer, admin
  PRIMARY KEY (user_id, role)

auth_codes
  id           uuid PK
  phone        text NOT NULL                  -- INDEX (phone, created_at DESC)
  code         char(6) NOT NULL
  attempts     int NOT NULL DEFAULT 0
  created_at   timestamptz NOT NULL
  expires_at   timestamptz NOT NULL
  used_at      timestamptz NULL
  revoked_at   timestamptz NULL

refresh_tokens
  id           uuid PK
  user_id      uuid FK -> users(id) ON DELETE CASCADE  -- INDEX
  token_hash   text NOT NULL UNIQUE           -- sha256 от токена
  created_at   timestamptz NOT NULL
  expires_at   timestamptz NOT NULL
  revoked_at   timestamptz NULL
```

Код действующий, если `used_at IS NULL AND revoked_at IS NULL AND expires_at > now AND attempts < 5`. Роли вынесены в отдельную таблицу, а не в массив: проверка роли — обычный запрос, а ограничение enum защищает от мусорных значений. Пользователь не связан с `auth_codes` внешним ключом: код запрашивается до того, как пользователь существует.

### Конкурентность
- **Запрос и проверка кода** выполняются под `pg_advisory_xact_lock(hashtext(phone))`. Это сериализует операции по одному номеру, даже когда строк ещё нет: проверка интервала в 60 секунд, отмена прежних кодов, учёт попыток и создание пользователя.
- **Создание пользователя** дополнительно защищено `UNIQUE(phone)`: при первом входе используется `INSERT ... ON CONFLICT (phone) DO NOTHING` и последующий `SELECT`.
- **Ротация refresh-токена** — один атомарный `UPDATE refresh_tokens SET revoked_at = now WHERE token_hash = :h AND revoked_at IS NULL AND expires_at > now RETURNING user_id`. Если строка не вернулась, ответ 401. Из двух одновременных запросов строку получает только один.
- **Уникальность email и телефона** обеспечивается индексами. `IntegrityError` по ним преобразуется в 409.

### Токены
- **Access** — JWT HS256 с секретом `JWT_SECRET`, claims `sub` (user id), `roles`, `type=access`, `iat`, `exp` (15 минут).
- **Refresh** — случайная строка `secrets.token_urlsafe(32)`. В БД хранится только SHA-256: утечка БД не даёт рабочих refresh-токенов.
- Токены возвращаются в теле ответа: `{access_token, refresh_token, token_type: "bearer", expires_in, refresh_expires_in}`. Это расходится с упоминанием httpOnly-cookie в `docs/nfr.md`, поэтому документ обновляется.
- Права (`admin`) и заполненность профиля проверяются по пользователю, загруженному из БД на каждом запросе, а не по claims токена. Тогда заполнение профиля снимает ограничение сразу, без перевыпуска токена.

### Роль администратора
`ADMIN_PHONES` — список номеров через запятую, нормализуемых к E.164 при загрузке настроек. При `verify` и `refresh` сервис добавляет или удаляет строку `admin` в `user_roles`. Роли `participant` и `organizer` вставляются при создании пользователя.

### Коды входа
6 цифр через `secrets.randbelow(10**6)` с дополнением нулями. Коды хранятся открыто, потому что их возвращает тестовая ручка. Неверная попытка увеличивает `attempts` у последнего действующего кода номера. Если действующего кода нет, ответ 400 без изменений.

### Тестовая ручка
Роутер регистрируется всегда, но при `AUTH_TEST_ENDPOINTS=false` отвечает 404 — так поведение проверяется тестом в обоих режимах без пересоздания приложения. По умолчанию настройка выключена. В `.env.example` она включена, с комментарием, что это только для разработки.

### Телефон
Номер нормализуется через `phonenumbers` с регионом по умолчанию `RU` и проверкой `is_valid_number`: `8 (999) 123-45-67` и `+7 999 123 45 67` дают `+79991234567`.

### Время
Сервисы получают текущее время из зависимости `now()` в `app/clock.py`. Тесты подменяют её фиксированным или сдвигаемым значением. Все метки — `timestamptz` в UTC. `age` вычисляется из `birth_date` и даты из `now()`.

### Ошибки
Единый формат `{"detail": {"code": "<machine_code>", "message": "<текст>"}}`. Коды: `invalid_phone`, `code_cooldown` (429, с `retry_after`), `invalid_code`, `invalid_token`, `profile_incomplete`, `forbidden`, `not_found`, `phone_taken`, `email_taken`. Ошибки валидации Pydantic остаются стандартными 422.

### Запуск и тесты
`compose.yaml` описывает сервисы `db` (postgres:16) и `api`. При старте `api` выполняет `alembic upgrade head`, затем запускает `uvicorn`. Тесты работают на отдельной БД `app_test` того же контейнера PostgreSQL, создаваемой init-скриптом. Перед сессией тестов применяются миграции, между тестами таблицы очищаются через `TRUNCATE ... CASCADE`. Команда: `docker compose run --rm api pytest`.

## Risks / Trade-offs

- [Коды хранятся открыто] → приемлемо, пока нет реальной отправки SMS. При подключении SMS-провайдера тестовая ручка убирается, а код хешируется.
- [Тестовая ручка включена в рабочем окружении] → выключена по умолчанию в `Settings`, а при старте с включённой ручкой пишется предупреждение в лог.
- [Access-токен живёт до 15 минут после смены телефона или снятия роли admin] → права проверяются по БД на каждом запросе, поэтому снятая роль `admin` перестаёт действовать сразу после синхронизации. Остаётся только окно до истечения access-токена после смены телефона, и оно принято.
- [Advisory-лок по `hashtext(phone)` может совпасть для разных номеров] → коллизия даёт лишь лишнее ожидание, не ошибку.
- [Админ может назначить пользователю номер из `ADMIN_PHONES`] → тот станет админом на следующем `refresh`. Изменять телефоны может только админ, поэтому риск принят.

## Migration Plan

Первая миграция на пустой БД, данных для переноса нет. Откат — `alembic downgrade base`.
