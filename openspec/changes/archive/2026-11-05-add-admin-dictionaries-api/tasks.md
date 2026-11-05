# Tasks

## 1. Уникальность названий без учёта регистра

- [x] 1.1 Миграция `0006_dictionary_names`:
  - проверка дублей по `lower(name)` с понятной ошибкой;
  - замена `uq_categories_name` и `uq_cities_name` на уникальные индексы `uq_categories_name_lower` и `uq_cities_name_lower`;
  - то же описание в моделях `Category` и `City`.

  Проверить: `alembic upgrade head`, `alembic downgrade 0005`, снова `alembic upgrade head` и `alembic check` без расхождений.
- [x] 1.2 Тесты в `test_db_constraints.py`: вставка «москва» при существующей «Москва» и «кино» при «Кино» отклоняется БД. Тест в `test_migrations.py`: данные до `0006` переживают миграцию. Проверить: `pytest tests/test_db_constraints.py tests/test_migrations.py`.

## 2. Backend: справочник городов

- [x] 2.1 Схема `CityWrite` и `dictionary_service`: создание, переименование, удаление города. Удаление: проверка мероприятий, затем перевод нарушения `fk_events_city_id_cities` в 409 `city_in_use`. Занятое название по `uq_cities_name_lower` — 409 `city_name_taken`. Ручки `POST /cities`, `PATCH /cities/{id}`, `DELETE /cities/{id}` с `AdminUser`.
- [x] 2.2 Тесты в `test_cities.py`:
  - права: 401, 403 `profile_incomplete`, 403 `forbidden`;
  - создание с обрезкой пробелов, место в алфавитном списке;
  - длина 60 и 61, пустое имя, `null`, лишнее поле — 422;
  - переименование видно в мероприятии и профиле, смена регистра своего имени — 200, 404;
  - занятое имя в другом регистре — 409;
  - одновременное создание: ровно один 201;
  - удаление: город очищается в профиле; город с прошедшим мероприятием — 409 `city_in_use`; несуществующий — 404.

  Проверить: `pytest tests/test_cities.py`.

## 3. Backend: справочник категорий

- [x] 3.1 Схема `CategoryUpdate`, multipart `POST /categories` (`name`, `icon`, `file`) с проверкой полей той же схемой, `PATCH /categories/{id}`, `PUT /categories/{id}/cover` (обработка файла до `FOR UPDATE`, удаление прежней картинки), `DELETE /categories/{id}` (удаление картинки, 409 `category_in_use`, перевод FK), 409 `category_name_taken`; все ручки с `AdminUser`.
- [x] 3.2 Тесты в `test_categories.py`:
  - права: 401, 403 `profile_incomplete`, 403 `forbidden`;
  - создание: обрезка пробелов, картинка и её `thumb` доступны, новая категория в конце `GET /categories`;
  - валидация: длина 50 и 51, пустое имя, иконка `video`, без файла — 422; файл ровно 2 МБ проходит, 2 МБ + 1 — `photo_too_large`; текст `cover.jpg` — `photo_invalid`;
  - `PATCH`: переименование видно в мероприятии, `icon: null` — 422, 404;
  - уникальность: «кино» при «Кино» — 409, «КИНО» для самой «Кино» — 200, одновременное создание — ровно один 201;
  - замена картинки: новый `cover_id`, старый — 404; файл 3 МБ — 422 без изменений; две одновременные замены — одна картинка в БД;
  - удаление: интерес пользователя пропадает, картинка — 404; категория с прошедшим мероприятием — 409 `category_in_use`; несуществующая — 404.

  Проверить: `pytest tests/test_categories.py`.

## 4. Backend: гонки удаления со ссылками

- [x] 4.1 Перевод нарушения внешних ключей `fk_events_category_id_categories` / `fk_events_city_id_cities` в 422 `category_not_found` / `city_not_found` в `create_event` и `update_event`. Перевод `fk_users_city_id_cities` и `fk_user_interests_category_id_categories` в те же 422 в `profile_service._save`.
- [x] 4.2 Тесты гонок (потоки с `threading.Barrier`, как в существующих тестах):
  - удаление категории и города одновременно с созданием мероприятия в них: либо 409 и мероприятие есть, либо 204 и 422;
  - удаление одновременно с `PATCH /profile` (город, интересы): в итоге в профиле нет удалённой записи, ответы 204 и 200 или 422.

  Проверить: `pytest tests/test_categories.py tests/test_cities.py`.
- [x] 4.3 Обновить реестр открытых ручек в `tests/test_access_profile_incomplete.py` (новые ручки черновику — 403 `profile_incomplete`). Затем проверить весь backend: `docker compose run --rm api pytest` и `docker compose run --rm api sh -c "ruff check . && ruff format --check . && mypy"`.

## 5. Документация

- [x] 5.1 `docs/architecture.md`: справочники меняют миграции и администратор через API, уникальность по `lower(name)`, перевод FK-ошибок при гонках. `docs/backlog.md`: убрать оба пункта «Управление категориями через API», пункт «Добавление городов пользователями» уточнить. Проверить: `grep -rn "пополняется только миграциями\|меняются только миграциями" docs` ничего не находит (фразы о схеме БД — «Схема меняется только миграциями Alembic» — остаются).

## 6. Проверка на запущенном API

- [x] 6.1 На `docker compose up --build` под администратором (телефон из `ADMIN_PHONES`) через `/api/docs`:
  - создать город и категорию с картинкой, переименовать, заменить картинку;
  - убедиться, что форма создания мероприятия во фронтенде после перезагрузки видит новые записи;
  - удалить использованную запись — 409, неиспользованную — 204.

## Workflow follow-up

- После ревью — `/opsx:archive` и синхронизация спек `events` и `cities`.
