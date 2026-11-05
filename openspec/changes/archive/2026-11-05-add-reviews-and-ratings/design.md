# Design

## Context

Мотивация и рамка — в `proposal.md`, требования — в `specs/reviews`, `specs/events`, `specs/user-profile` и `specs/web-app`.

Что в текущем коде определяет подход:

- Организатор записан в `event_participants`, как и участники. После `starts_at` запись, отказ, исключение, изменение и удаление мероприятия запрещены (`event_started`). Поэтому к моменту открытия окна отзывов (`starts_at` + 24 ч) состав участников, организатор, `starts_at` и название уже не меняются. Блокировки для проверки «автор и получатель были на мероприятии» не нужны.
- `organizer_id` мероприятия изменить нельзя (`PATCH` отклоняет его с 422). Поэтому вид отзыва (`organizer` / `participant`) можно один раз вычислить при создании и сохранить.
- Слои: роутеры → сервисы → модели. Текущее время приходит через `NowDep`, что позволяет тестировать границы окна. Доступ к чужому профилю проверяется в `profile_service.get_profile_for`. Заполненный профиль требует `CompletedUser`.
- Вид мероприятия собирается одним запросом `event_service._view_query` со скалярными подзапросами (`_participants_count`, `_photo_ids`).

## Goals / Non-Goals

**Goals:**
- Рейтинг всегда совпадает с текущим набором отзывов, без фоновых пересчётов.
- Уникальность отзыва и гонки при создании решаются ограничением БД.
- Анонимность обеспечивается на сервере: клиент никогда не получает автора анонимного отзыва, если он не администратор и не сам автор.

**Non-Goals:**
- Кеширование и денормализация рейтинга в таблице `users`.
- Общий механизм «окон» для других сущностей: правило окна живёт в сервисе отзывов.

## Decisions

### Схема БД: таблица `reviews` (миграция `0007_reviews`)

```
reviews
  id           uuid PK default gen_random_uuid()
  event_id     uuid NULL  FK events.id ON DELETE SET NULL
  event_title  varchar(100) NOT NULL       -- копия названия на момент создания
  author_id    uuid NOT NULL FK users.id ON DELETE CASCADE
  target_id    uuid NOT NULL FK users.id ON DELETE CASCADE
  kind         review_kind NOT NULL        -- enum ('organizer', 'participant')
  stars        smallint NOT NULL CHECK (stars BETWEEN 1 AND 5)
  text         varchar(1000) NULL
  anonymous    boolean NOT NULL DEFAULT false
  created_at   timestamptz NOT NULL
  updated_at   timestamptz NOT NULL
  CHECK (author_id <> target_id)
  UNIQUE (event_id, author_id, target_id)  -- uq_reviews_event_author_target
  INDEX ix_reviews_target_kind_created (target_id, kind, created_at DESC, id DESC)
```

- `ON DELETE SET NULL` и `event_title` реализуют требование «Отзывы после удаления мероприятия». Альтернатива — запретить удаление мероприятия с отзывами (`RESTRICT`). Отклонена: противоречит решению «отзывы оставить».
- `NULL` в `event_id` не участвует в уникальности. Это допустимо: после удаления мероприятия новых отзывов по нему быть не может.
- Индекс `(target_id, kind, …)` обслуживает и агрегат рейтинга, и постраничный список отзывов о пользователе.
- Миграция создаёт enum `review_kind`, таблицу и индекс. `downgrade` удаляет таблицу и enum. Данных для переноса нет.

### Рейтинг считается запросом, а не хранится

Агрегат: `count(*)` и `round(avg(stars)::numeric, 1)` по `(target_id, kind)`. Если `count < 3`, отдаётся `null`. `round` для `numeric` в PostgreSQL округляет половину от нуля, а для положительных оценок это и есть «половина — вверх» (4.75 → 4.8).

- Альтернатива — счётчики `sum`/`count` в `users`, которые обновляются в транзакции отзыва. Отклонена: пришлось бы блокировать строку получателя при каждом создании, изменении и удалении, включая удаление администратором, а выигрыш при текущих объёмах ничтожен.
- Общий хелпер `rating_subquery(user_id_column, kind)` в `review_service` возвращает скалярный подзапрос со средним или `NULL`. Его используют:
  - `event_service._view_query` для `organizer.rating`, с видом `organizer` (каталог и `GET /events/{id}`);
  - `event_service.list_participants`, где вид выбирается через `CASE WHEN user_id = organizer_id THEN 'organizer' ELSE 'participant' END`;
  - `profile_service.build_profile`: два агрегата `average` + `count` одним запросом с `GROUP BY kind`.

### Окно отзывов и порядок проверок

`opens_at = starts_at + 24h`, `closes_at = starts_at + 8d`. Окно открыто, если `opens_at <= now < closes_at`. Функции окна лежат в `review_service` и принимают `now` из `NowDep`.

Порядок проверок при создании: мероприятие существует (404) → автор записан (403 `not_participant`) → окно (409) → получатель записан и это не сам автор (422 `review_target_invalid`) → вставка. Получатель проверяется после окна: так в тестах ошибка окна не маскируется ошибкой о получателе. Спека требует только «окно после прав», и этот порядок ей соответствует.

Изменение и удаление: отзыв существует (404) → права (автор; для удаления — автор или администратор, иначе 403) → окно (только для автора). Если `event_id IS NULL` (мероприятие удалено), окно для автора считается закрытым (`review_closed`).

### Гонки

- Одновременное создание: вставку ловит `UNIQUE`, `IntegrityError` по `uq_reviews_event_author_target` превращается в 409 `review_exists`, как это сделано для уникальных имён справочников.
- Одновременное удаление: `DELETE … RETURNING id`. Если строк не вернулось — 404.
- Одновременное изменение одного отзыва автором: `SELECT … FOR UPDATE` по отзыву. Итог — одно из изменений целиком.

### API и слои

- Новый роутер `app/routers/reviews.py` без общего префикса:
  - `POST /events/{event_id}/reviews`
  - `GET /events/{event_id}/reviews/mine`
  - `PATCH /reviews/{review_id}`
  - `DELETE /reviews/{review_id}`
  - `GET /users/{user_id}/reviews`

  Все ручки используют `CompletedUser`. Ручка `/users/{id}/reviews` проверяет доступ через `profile_service.get_profile_for`, поэтому правило совпадает с профилем без дублирования.
- Схемы в `app/schemas/review.py`:
  - `ReviewCreate` и `ReviewUpdate` с `extra="forbid"`: `stars` `conint(1..5)`, `text` обрезается, пустой становится `None`;
  - `ReviewOut`, `ReviewEventRef`, `ReviewAuthor`, `ReviewPage`, `MyReviews` (`items`, `opens_at`, `closes_at`);
  - `RatingOut` (`average: float | None`, `count: int`).
- `author` маскируется в одном месте, `review_service.to_out(review, viewer)`: автор `null`, если `anonymous` и `viewer` не администратор и не автор. Роутеры получают уже маскированные схемы.
- `OrganizerOut` и `ParticipantOut` получают `rating: float | None`, `ProfileOut` — `ratings: ProfileRatings`. Поля только добавляются, существующие клиенты не ломаются.

### Frontend

- `web/src/api/reviews.ts` содержит типы и вызовы. В `api/events.ts` и `api/profile.ts` добавляются новые поля.
- `utils/format.ts`:
  - `formatRating(4.8)` → «4,8»;
  - `pluralReviews(n)` → «1 отзыв / 3 отзыва / 12 отзывов».
- Компоненты:
  - `RatingBadge.vue` — звезда `pi-star-fill` и число, ничего при `null`;
  - `ReviewDialog.vue` — `Dialog` по стандарту окон, `Rating` из PrimeVue 4 с увеличенными звёздами, чтобы цель нажатия была не меньше 44 px, `Textarea` со счётчиком, `Checkbox`, «Удалить отзыв» через `ConfirmDialog`;
  - `ProfileReviews.vue` — `Tabs`, список и «Показать ещё».
- `EventModal.vue` запрашивает `GET /events/{id}/reviews/mine`, только если пользователь записан и мероприятие началось. Из ответа он вычисляет состояние окна по `opens_at`/`closes_at` и текущему времени и передаёт его в `EventParticipants.vue` вместе с картой «получатель → мой отзыв». Сервер остаётся источником истины: ответ 409 обрабатывается по спеке.
- `UserProfileView.vue` получает две плитки рейтинга в сетке `profile-stats` (на мобильной ширине они стоят в одну колонку) и раздел `ProfileReviews`. После удаления отзыва администратором профиль запрашивается заново, чтобы обновить плитки и счётчики вкладок.

## Risks / Trade-offs

- [Скалярный подзапрос рейтинга на каждой карточке каталога] → Индекс `(target_id, kind, …)`. На странице до 100 карточек, агрегат по индексу дешёвый. Если станет узким местом, можно перейти на денормализацию, не меняя API.
- [Утечка автора анонимного отзыва] → Маскирование в одной функции. Тесты на каждую ручку, которая возвращает отзыв (создание, изменение, мои отзывы, список о пользователе), с ролями «получатель», «третье лицо», «администратор», «автор».
- [Часы клиента расходятся с сервером, и кнопка «Оценить» видна при закрытом окне] → Сервер отвечает 409 `review_closed` или `review_not_open`, клиент показывает сообщение и обновляет данные.
- [Предстоящее мероприятие удалят до начала, а отзывов по нему ещё нет] → Не влияет: отзывы возможны только после `starts_at` + 24 ч, а удаление после начала запрещено.
- [Удаление пользователя каскадно удаляет его отзывы] → Ручки удаления пользователя сейчас нет. Поведение зафиксировано `ON DELETE CASCADE` и пересматривается вместе с такой ручкой.

## Migration Plan

1. Миграция `0007_reviews` (`alembic upgrade head`) только добавляет таблицу и enum. Её можно выкатывать до кода.
2. Затем выкатываются backend и frontend. Новые поля в ответах опциональны для старого клиента.
3. Откат: откатить код, затем `alembic downgrade 0006`. Отзывы будут удалены.
