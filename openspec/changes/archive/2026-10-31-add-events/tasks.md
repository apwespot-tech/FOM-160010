# Tasks

## 1. Схема БД и категории

- [x] 1.1 Добавить модели `Category`, `Event`, `EventParticipant` в `app/models/event.py` и экспорт в `app/models/__init__.py`; проверка — `mypy` без ошибок
- [x] 1.2 Написать миграцию `0002_events`: таблицы, CHECK-ограничения, индексы, начальные категории через `op.bulk_insert`, `downgrade` удаляет таблицы; проверка — `alembic upgrade head` и `alembic downgrade 0001` проходят на `app_test`
- [x] 1.3 Обновить `tests/conftest.py`: `events` и `event_participants` в `TRUNCATE` (без `categories`), хелперы `create_event`, `set_roles`; добавить в `test_db_constraints.py` проверки CHECK для `max_participants`, `min_age`, `duration_minutes` и PK участника; проверка — `pytest tests/test_db_constraints.py`
- [x] 1.4 Реализовать `GET /categories` (схема `CategoryOut`, роутер `categories`, подключение в `main.py`) и тесты требования «Справочник категорий» (список по `id`, четыре начальные категории, `profile_incomplete`, 401); проверка — `pytest tests/test_categories.py`

## 2. Создание и просмотр мероприятий

- [x] 2.1 Вынести `calculate_age` в общий модуль и переиспользовать в `ProfileOut`; добавить в `deps.py` `require_role`, `OrganizerUser`, `ParticipantUser`; проверка — существующие тесты профиля проходят
- [x] 2.2 Описать схемы `EventCreate`, `EventUpdate`, `EventOut`, `EventPage`, `ParticipantOut` с валидацией из требования «Валидация полей мероприятия» (обрезка строк, `AwareDatetime`, диапазоны, набор `min_age`, `extra="forbid"` для `EventUpdate`); проверка — unit-тесты схем в `test_unit.py`
- [x] 2.3 Реализовать в `event_service` создание мероприятия с автоматической записью организатора и общий запрос мероприятия с `participants_count`, `is_joined`, категорией и организатором; ручки `POST /events` и `GET /events/{id}`; проверка — тесты требований «Создание мероприятия», «Представление мероприятия», «Просмотр мероприятия», «Валидация полей мероприятия» в `tests/test_events_crud.py`, включая границы `max_participants` 2/100, `starts_at` = now, 403 без роли `organizer`, `category_not_found`

## 3. Каталог

- [x] 3.1 Реализовать `GET /events`: только предстоящие, сортировка `starts_at, id`, фильтры `category_id`, `from`, `to`, пагинация `limit`/`offset` с `total`, один запрос на страницу плюс подсчёт; проверка — тесты требования «Каталог мероприятий» в `tests/test_events_catalog.py` (прошедшие скрыты, граница `to` исключена, `limit=101` → 422, `offset` за пределами)

## 4. Изменение и удаление

- [x] 4.1 Реализовать блокировку строки мероприятия (`FOR UPDATE`) и проверки «автор или админ» и `event_started` в сервисе; проверка — используется во всех изменяющих операциях групп 4 и 5
- [x] 4.2 Реализовать `PATCH /events/{id}` с частичным обновлением, запретом `null` для обязательных полей, проверкой новой даты и `limit_below_participants`; проверка — тесты требований «Изменение мероприятия» и «Лимит не ниже числа участников» в `tests/test_events_crud.py`, включая лимит, равный числу участников, и 403 для участника
- [x] 4.3 Реализовать `DELETE /events/{id}` (жёсткое удаление с записями); проверка — тесты требования «Удаление мероприятия» и сценариев `event_started` для `PATCH` и `DELETE`, в том числе для администратора, в `tests/test_events_crud.py`

## 5. Участие

- [x] 5.1 Реализовать `POST /events/{id}/join` с порядком проверок из design.md (роль, 404, `event_started`, `already_joined`, `age_restricted`, `event_full`); проверка — тесты требований «Запись на мероприятие», «Возрастное ограничение при записи» (17 лет, 18 сегодня, 18 до мероприятия) и «Лимит мест при записи» в `tests/test_events_participation.py`
- [x] 5.2 Реализовать `POST /events/{id}/leave` (`not_joined`, `organizer_cannot_leave`, `event_started`); проверка — тесты требования «Отказ от участия», включая повторную запись после отказа
- [x] 5.3 Реализовать `POST /events/{id}/participants/{user_id}/remove` (права, `participant_not_found`, `organizer_cannot_leave`, `event_started`); проверка — тесты требования «Удаление участника организатором», включая повторную запись удалённого
- [x] 5.4 Реализовать `GET /events/{id}/participants` (порядок записи, только `id` и `name`, 403 без раскрытия существования, 404 для админа); проверка — тесты требования «Список участников», включая бывшего участника и прошедшее мероприятие
- [x] 5.5 Написать конкурентные тесты на потоках с `threading.Barrier`: одновременная запись на последнее место, двойной `leave`, уменьшение лимита одновременно с записью; проверка — `pytest -k concurrent` проходит в 5 запусках подряд
- [x] 5.6 Проверить требование «Доступ к ручкам мероприятий»: 401 без токена и `profile_incomplete` для черновика на каждой новой ручке (параметризованный тест); проверка — `pytest tests/test_events_participation.py`

## 6. Документация и итоговая проверка

- [x] 6.1 Обновить `docs/project.md` («Подача заявки на участие» → «Запись на мероприятие»), добавить пункты «Вне scope» этого изменения в `docs/backlog.md`, при необходимости — ручки в `README.md`; проверка — ссылки и формулировки соответствуют спеке `events`
- [x] 6.2 Прогнать полный набор проверок backend: `pytest`, `ruff check`, `ruff format --check`, `mypy`; и вручную в Swagger (`/api/docs`) создать мероприятие, записаться вторым пользователем, получить список участников; проверка — все команды без ошибок, сценарий проходит

## Workflow follow-up

- Закоммитить изменение, затем выполнить `/opsx:archive add-events` с синхронизацией спеки `events`.
