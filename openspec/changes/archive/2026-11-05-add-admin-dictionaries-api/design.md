# Design

## Context

- `categories (id, name varchar(50) UNIQUE uq_categories_name, icon CHECK ^pi-[a-z0-9-]+$, cover_id FK category_covers RESTRICT)`, `category_covers (data, thumb, content_type)`.
- `cities (id, name varchar(60) UNIQUE uq_cities_name)`.
- Ссылки:
  - `events.category_id`, `events.city_id` — `RESTRICT`;
  - `user_interests.category_id` — `CASCADE`;
  - `users.city_id` — `SET NULL`.
- Имена ограничений задаёт соглашение в `app/models/base.py`, например `fk_events_category_id_categories`.
- Права администратора — зависимость `AdminUser`: заполненный профиль и роль `admin`, иначе 403.
- Обработка картинок готова: `photo_processing.read_limited` и `process_photo` проверяют тип по содержимому и размер, делают WebP-копию. Картинки категорий отдаёт `photo_service.get_category_cover`.
- Существование категории и города проверяют `_ensure_category_exists` / `_ensure_city_exists` в `event_service` и аналогичные проверки в `profile_service._apply_common_fields`. Это проверка без блокировки строки.
- Пример замены картинки под блокировкой строки — `profile_image_service` для аватара и обложки.

## Goals / Non-Goals

**Goals:**
- Гонки «удаление записи из справочника / ссылка на неё» решает БД (внешние ключи), а сервисы только переводят ошибку в понятный код.
- Обработка картинок категорий та же, что у фото мероприятий и картинок профиля.

**Non-Goals:**
- Аудит действий администратора и история изменений справочников.
- Инвалидация кеша справочников на клиенте.

## Decisions

### 1. Сервис `dictionary_service` и ручки в существующих роутерах

Ручки добавляются в `routers/categories.py` и `routers/cities.py` рядом с `GET`, все с зависимостью `AdminUser`. Логику держит новый `services/dictionary_service.py`: создание, изменение и удаление категорий и городов, замена картинки. Существующий `list_categories` остаётся в `event_service`.

- Альтернатива — префикс `/admin/...`. Отказались: в проекте права определяет зависимость, а не адрес. Так уже устроен `PATCH /profile/{id}`.

### 2. Схемы запросов

- `CategoryUpdate` и `CityWrite`: `extra="forbid"`, `name` — `strip_whitespace`, 1–50 (категория) или 1–60 (город) символов. Очистка через `null` даёт 422 (по образцу `ProfileUpdate.required_fields_not_cleared`). `icon` проверяется по `ICON_PATTERN`.
- `POST /categories` — multipart. Поля `name` и `icon` идут через `Form`, затем проверяются той же схемой, чтобы правила и ошибки 422 совпадали с `PATCH`. Файл `file` обязателен.

### 3. Уникальность без учёта регистра — миграция `0006_dictionary_names`

```
 categories: DROP CONSTRAINT uq_categories_name
             CREATE UNIQUE INDEX uq_categories_name_lower ON categories (lower(name))
 cities:     DROP CONSTRAINT uq_cities_name
             CREATE UNIQUE INDEX uq_cities_name_lower ON cities (lower(name))
```

`downgrade` возвращает прежние ограничения. Текущие данные дублей по регистру не содержат: это проверяет миграция, она падает с понятным сообщением, если дубль найден. В моделях ограничение описывается как `Index(..., func.lower(text("name")), unique=True)` по образцу `uq_users_email_lower`, тогда `alembic check` расхождений не покажет.

Занятое название ловится по `IntegrityError` с именем индекса и превращается в 409 `category_name_taken` / `city_name_taken`. Предварительной проверки нет: индекс сам даёт «ровно один успешен» при одновременных запросах.

### 4. Удаление и гонки со ссылками

```
 DELETE /categories/{id}
   lock categories row FOR UPDATE      -- против одновременной замены картинки
   EXISTS events WHERE category_id     -> 409 category_in_use
   DELETE categories                   -- user_interests уходят каскадом
   DELETE category_covers (old cover)
   commit; IntegrityError(fk_events_category_id_categories) -> 409 category_in_use
```

- Предварительная проверка `EXISTS` даёт понятный ответ в обычном случае. Если мероприятие вставляется одновременно с удалением, PostgreSQL блокирует ссылаемую строку (`FOR KEY SHARE`), и одна из транзакций получает ошибку внешнего ключа:
  - удаление → `IntegrityError` по `fk_events_category_id_categories` → 409 `category_in_use`;
  - создание или изменение мероприятия → `IntegrityError` по тому же FK → 422 `category_not_found`. Для этого `create_event` и `update_event` получают перевод ошибки FK в 422, как `_save` в профиле переводит нарушение уникальности.
- Города устроены так же, только профили пользователей не блокируют удаление (`SET NULL`). Если `PATCH /profile` с удаляемым городом проиграл гонку, он получает ошибку FK, и `profile_service._save` переводит её в 422 `city_not_found`. Интересы с удаляемой категорией — так же, 422 `category_not_found`.

### 5. Замена картинки категории

Под `SELECT ... FOR UPDATE` строки категории: новая строка `category_covers`, перестановка `cover_id`, удаление прежней картинки — по образцу `profile_image_service`. Файл читается и обрабатывается до блокировки, чтобы не держать её во время работы Pillow. При одновременных заменах вторая транзакция ждёт первую и удаляет уже её картинку, поэтому лишних картинок не остаётся.

### Схема БД

Одна миграция `0006`: уникальность названий по `lower(name)` для `categories` и `cities` (решение 3). Других изменений схемы нет.

## Risks / Trade-offs

- [Администратор удалил категорию, а у пользователя в открытой форме старый справочник] → Сохранение получает 422 `category_not_found` у поля. Справочник обновится после перезагрузки страницы.
- [Опечатка в иконке (`pi-vidoe`) даёт пустую иконку в интерфейсе] → Проверяется только формат. Исправить можно через `PATCH`.
- [Переименование меняет отображение старых, в том числе прошедших, мероприятий] → Это ожидаемо: категория — общий справочник, а не снимок на момент создания.

## Migration Plan

`alembic upgrade head` применяет `0006` при старте контейнера `api`. Откат — `alembic downgrade 0005`: возвращает уникальность с учётом регистра. Он всегда проходит, потому что под индексом `lower(name)` названий, различающихся только регистром, быть не может. Ручки администратора при откате кода пропадают, а записи, созданные через них, остаются. Frontend не меняется.
