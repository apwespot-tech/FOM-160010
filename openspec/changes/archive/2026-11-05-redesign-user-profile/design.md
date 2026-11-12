# Design

## Context

- Пользователь: `users (id, phone, name, birth_date, email, telegram, photo_url, created_at, …)`; профиль — `ProfileOut.from_user`, изменение — `ProfileUpdate` (`extra="forbid"`), доступ к чужому — `profile_service.get_profile_for` (сейчас только себе и админу).
- `photo_url` используется в `ProfileOut`, в `organizer` мероприятия (`_view_query` → `EventView.organizer_photo_url`) и в списке участников (`list_participants`); на frontend — `PersonAvatar`, `ProfileCard`, `OrganizerCard`, `EventParticipants`.
- Картинки мероприятий и категорий уже хранятся в БД с уменьшенными копиями и отдаются с `private, immutable`; обработка — `services/photo_processing.py` (`read_limited`, `process_photo` с `thumb`); frontend — `apiFetchBlob` и кеш `usePhotoUrl`/`useImageUrl`.
- Справочник категорий заполняется миграциями — так же будет справочник городов.
- Страница профиля — `ProfileView.vue` + `ProfileCard.vue` + `ProfileForm.vue`/`useProfileForm`, маршрут `/profile`.

## Goals / Non-Goals

**Goals:**
- Доступ к чужому профилю определяется одним SQL-условием «есть общее мероприятие» и проверяется на backend.
- Картинки профиля — тем же механизмом, что фото мероприятий (обработка, копии, кеш по `id`).
- Одна страница профиля для своего и чужого, без дублирования вёрстки.

**Non-Goals:**
- Фильтр каталога по городу, рейтинг — в бэклог.
- Перенос картинок по существующим `photo_url` (загрузка с чужих адресов — риск SSRF).
- Админские операции с картинками чужих профилей.

## Decisions

### 1. Схема БД и миграция `0005_profile`

```
 cities (id identity PK, name varchar(60) UNIQUE)               -- ~40 городов, миграцией
 user_images (id uuid PK, user_id uuid FK users CASCADE,
              content_type CHECK, data bytea, thumb bytea, created_at)
 users  + about varchar(500) NULL
        + city_id  int  FK cities  SET NULL     NULL
        + avatar_id uuid FK user_images SET NULL NULL
        + cover_id  uuid FK user_images SET NULL NULL
        - photo_url
 user_interests (user_id uuid FK users CASCADE, category_id int FK categories CASCADE,
                 PK (user_id, category_id))
 events + city_id int FK cities RESTRICT NOT NULL
```

Шаги `upgrade`: создать `cities` и заполнить списком (Москва, Санкт-Петербург, Новосибирск, Екатеринбург, Казань, Нижний Новгород, Красноярск, Челябинск, Самара, Уфа, Ростов-на-Дону, Краснодар, Омск, Воронеж, Пермь, Волгоград, Тюмень, Саратов, Тольятти, Ижевск, Барнаул, Иркутск, Хабаровск, Владивосток, Ярославль, Калининград, Томск, Оренбург, Кемерово, Новокузнецк, Рязань, Набережные Челны, Пенза, Липецк, Тула, Киров, Чебоксары, Астрахань, Махачкала, Сочи); `user_images`, `user_interests`; новые столбцы `users`; `events.city_id` nullable → `UPDATE events SET city_id = <Москва>` → `NOT NULL`; удалить `users.photo_url`. `downgrade` возвращает `photo_url` (пустым) и удаляет остальное.

`user_images` — одна таблица для аватара и обложки: картинка принадлежит пользователю (`user_id`), а роль определяется ссылкой из `users.avatar_id`/`cover_id`. Так проверка «картинка этого пользователя» — одно условие, а каскад удаляет картинки вместе с пользователем. Циклическая ссылка `users` ↔ `user_images` разрешена через `use_alter` у FK `avatar_id`/`cover_id`.

`events.city_id` — `RESTRICT`: город нельзя удалить, пока на него ссылаются мероприятия. `users.city_id` — `SET NULL`: город профиля необязателен.

### 2. Доступ к чужому профилю

```python
shared = exists().where(
    a.event_id == b.event_id, a.user_id == viewer.id, b.user_id == owner_id
)  # a, b — aliased(EventParticipant)
```

Организатор всегда есть в `event_participants`, поэтому условие покрывает «участник ↔ организатор» и «участник ↔ участник»; прошедшие мероприятия входят, отказ от участия удаляет строку — и доступ пропадает. Порядок проверок в `get_profile_for`: свой id → 200; админ → 404/200; иначе одно `SELECT users … WHERE id = :id AND EXISTS(shared)` — нет строки → 403 (и для несуществующего, и для чужого: существование не раскрывается). Индекс `ix_event_participants_user_id` уже есть, второй стороне хватает PK `(event_id, user_id)`.

Ответ для всех, у кого есть доступ, — полный `ProfileOut` (решение пользователя: «все поля»). Правило «ответы мероприятий не раскрывают телефон и email» сохраняется: контакты видны только на странице профиля.

### 3. Представление профиля и счётчики

`ProfileOut` — новые поля `about`, `city`, `interests`, `avatar_id`, `cover_id`, `created_at`, `stats`; без `photo_url`. Счётчики — два `COUNT` при построении ответа (а не денормализация): `organized_count = count(events where organizer_id = :id)`, `attended_count = count(event_participants ⋈ events where user_id = :id and organizer_id <> :id and starts_at <= now)`. `from_user` получает `stats` и интересы из сервиса; `GET /profile` и `PATCH` тоже их возвращают.

### 4. Изменение профиля

`ProfileUpdate` + `about` (обрезка, пустая → `None`, ≤ 500), `city_id: int | None`, `interest_ids: list[int] | None` (`None` в `model_fields_set` — 422, не очистка; очистка — `[]`). Сервис проверяет существование города (`city_not_found`) и категорий (`category_not_found`), повтор в `interest_ids` — 422 валидатором схемы. Интересы заменяются целиком: `DELETE` + `INSERT` в одной транзакции с остальными полями. `AdminProfileUpdate` наследует новые поля.

### 5. Аватар и обложка

- `PUT /profile/avatar|cover` (multipart `file`): `read_limited` + `process_photo` (готовая проверка типа, EXIF, копия), затем под блокировкой строки пользователя (`SELECT … FOR UPDATE`) вставить `user_images`, переставить ссылку и удалить прежнюю картинку. Две одновременные загрузки сериализуются: побеждает вторая, первая картинка удаляется ею же — лишних картинок не остаётся.
- `DELETE` — обнулить ссылку и удалить картинку в той же транзакции.
- `GET /users/{id}/images/{image_id}?size=` (`CompletedUser`): `WHERE user_images.id = :image AND user_id = :id AND (users.avatar_id = :image OR users.cover_id = :image)`; заголовки — `PHOTO_HEADERS`. Доступ шире, чем к профилю, сознательно: аватар организатора виден в мероприятии незаписанным, а `image_id` появляется только в ответах, которые зритель уже имел право получить.

### 6. Мероприятия: город и аватары

`EventCreate.city_id: int` (обязателен), `EventUpdate.city_id: int | None` с запретом очистки; `_ensure_city_exists` по образцу категорий; `_view_query` добавляет `City` (JOIN) и `User.avatar_id` вместо `photo_url`; `EventOut.city`, `OrganizerOut.avatar_id`; `list_participants` — `avatar_id`. Новый роутер `GET /cities`.

### 7. Frontend

- Маршруты: `/users/:id` → `UserProfileView.vue`; `/profile` → редирект на `/users/<session.profile.id>` (через гард, где профиль уже загружен). Меню профиля ведёт туда же.
- `UserProfileView`: если `id` свой — данные из `GET /profile` (и обновление сессии после сохранения), иначе `GET /profile/{id}`; 403/404 → экран «Профиль недоступен».
- Компоненты: `ProfileHero` (обложка/полоса, аватар, имя, Telegram, «Поделиться», «Редактировать»), `ProfileAbout` (о себе, интересы через `CategoryTag`), `ProfileFacts` (город, «На сайте с», возраст, дата рождения, телефон, email), `ProfileStats` (две плитки). Существующие `ProfileCard`/`ProfileForm` перестраиваются: форма редактирования — общий `useProfileForm` (+ город, «О себе», интересы, черновики файлов аватара и обложки по образцу `PhotoDraft`).
- Сохранение: `PATCH` изменённых полей → `PUT`/`DELETE` аватара → то же для обложки; ошибка картинки после успешного `PATCH` оставляет форму открытой, повтор шлёт только картинки (как с фото мероприятий).
- `PersonAvatar` получает `userId` + `avatarId` и грузит картинку через `useImageUrl` (ключ `user:<avatar_id>:<size>`), иначе инициалы. Использования: профиль, `OrganizerCard`, `EventParticipants` (там же — ссылки `RouterLink` на `/users/:id`). Открытие профиля из окна мероприятия — обычный переход (окно закрывается).
- «Поделиться»: `navigator.share({ url })` при наличии, `AbortError` игнорируется; иначе `navigator.clipboard.writeText` + toast «Ссылка скопирована»; без буфера — toast со ссылкой.
- Город: `useCities()` (кеш справочника, как `useCategories`); в форме мероприятия `Select` с `filter` (40 вариантов), по умолчанию `session.profile.city?.id`; плитка «Где» и карточка — «Город, место».
- Онбординг не меняется (город не обязателен).

## Risks / Trade-offs

- [Расширение доступа раскрывает телефон, email и дату рождения всем, с кем пользователь был на одном мероприятии, бессрочно] → осознанное решение пользователя; правило проверяется на backend одним условием и покрыто тестами на каждую ветку; в `docs/nfr.md` правило защиты контактов переписывается явно.
- [Потеря существующих `photo_url`] → у MVP их мало и они не проверялись; показываются инициалы, пользователь загружает аватар заново. Записано в proposal (**BREAKING**).
- [Изображения профиля доступны любому пользователю по `id`] → `id` — UUID, приходит только в разрешённых ответах; контактов в картинках нет.
- [Счётчики — два `COUNT` на каждый ответ профиля] → по индексам `organizer_id`/`user_id` дёшево; при росте — денормализация.
- [Циклическая FK `users` ↔ `user_images`] → `use_alter` и `post_update` в модели; покрыто тестом удаления пользователя.

## Migration Plan

1. `0005` применяется при старте `api`: города, Москва для существующих мероприятий, удаление `photo_url`.
2. Frontend и backend выкатываются вместе (несовместимое поле `photo_url` → `avatar_id`).
3. Откат: `alembic downgrade 0004` — город мероприятий и картинки профилей теряются, `photo_url` возвращается пустым.

## Open Questions

Нет.
