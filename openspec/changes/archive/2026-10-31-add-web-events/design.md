# Design

## Context

- Backend мероприятий (`specs/events`) отдаёт каталог только предстоящих; фильтра «мои» нет. Схема БД для `scope`/`period` достаточна: `event_participants` и `events.organizer_id` уже есть, индексы `ix_events_starts_at`, `ix_event_participants_user_id`.
- Frontend (`web/`): Vue 3 + PrimeVue 4.5 (MIT), слой `api/` на `apiFetch` с разбором `detail.code` и ошибок Pydantic, Pinia-стор `session` (профиль с `age`), гард маршрутов `resolveRedirect`, стандарт «Окна и карточки с данными» в `docs/rules.md`, реализованный в `ProfileCard` + `useProfileForm`.
- Требования — в `specs/events` и `specs/web-app` этого изменения; мотивация — в proposal.md.

## Goals / Non-Goals

**Goals:**
- Главная страница и страница мероприятия полностью работают на 360 / 768 / 1280 px без горизонтальной прокрутки.
- Форма мероприятия одна для создания (в Dialog) и редактирования (на месте), с общей валидацией.
- Состояние списка (вкладка, период, фильтры) восстанавливается из адреса.

**Non-Goals:**
- Кеширование между страницами (стор мероприятий), оптимистичные обновления, бесконечная прокрутка.
- Реальные уведомления.

## Decisions

### Backend: `scope` и `period`

`list_upcoming_events` переименовывается в `list_events` и получает `scope` и `period` (Python `StrEnum`, FastAPI сам отвечает 422 на неизвестное значение). Условия:

```text
scope=all        -> без условия
scope=joined     -> EXISTS(участник = me) AND organizer_id <> me
scope=organized  -> organizer_id = me
period=upcoming  -> starts_at > now   ORDER BY starts_at ASC,  id ASC
period=past      -> starts_at <= now  ORDER BY starts_at DESC, id DESC
scope=all & period=past -> AppError(422, "past_requires_scope")
```

Проверка недопустимой комбинации — в сервисе, как и остальные правила (`docs/rules.md`: бизнес-логика не пишется в роутерах). `is_joined` в ответе не меняется: для своих мероприятий он `true`, поэтому клиент отличает «организатор» по `organizer.id === profile.id`.

Альтернатива — отдельные ручки `/events/joined`, `/events/organized`. Отклонена: дублируют фильтры и пагинацию, а клиенту удобнее один источник списка.

### Backend: возраст и свободные места

- Возрастной фильтр — только для `scope=all`: условие `min_age <= :age`, где возраст считается в сервисе через `calculate_age(user.birth_date, now.date())` — тем же правилом, что и при записи. В своих вкладках фильтр не нужен: туда попадают только те мероприятия, где пользователь уже участник или автор.
- `min_free_places` — условие `max_participants - (SELECT count(*) ...) >= :n` с тем же коррелированным подзапросом числа участников, что и в ответе. Параметр валидируется FastAPI (`Query(ge=1, le=100)`).
- Сигнатура `list_events` получает пользователя целиком (нужна дата рождения), а не только `id`.

### Маршруты и шапка

```text
/              EventsView   (meta.complete)   было: redirect -> /profile
/events/:id    EventView    (meta.complete)
/profile       ProfileView
/:pathMatch    redirect -> /
```

`resolveRedirect` для заполненного профиля возвращает `/` вместо `/profile`; `LoginView` и `OnboardingView` после успеха переходят на `/`.

Шапка (`App.vue`) разбивается на компоненты:
- `AppHeader.vue` — раскладка, ссылка «Мероприятия» (`RouterLink` с `active-class`), видимость по `session.isProfileCompleted`;
- кнопка «Создать мероприятие» внутри `AppHeader` открывает `CreateEventDialog`. Диалог монтируется один раз в `App.vue`, а открывается через `useCreateEventDialog()` (модульный `ref` и функция `open()`), поэтому ту же форму открывает и кнопка на пустой вкладке «Организую»;
- `NotificationsButton.vue` — `Button` + `Popover` с заглушкой;
- `ProfileMenu.vue` — `Button` с инициалами + `Menu` (popup) с пунктом-заголовком (имя, маскированный телефон через `formatPhone`), «Профиль», «Выйти».

`Menu` и `Popover` PrimeVue закрываются по `Esc` и клику снаружи сами.

### Главная страница: состояние в URL

`useEventListQuery()` читает и пишет `route.query`:

```text
?tab=joined|organized     (нет -> "Найти компанию", scope=all)
&period=past              (нет -> upcoming; игнорируется для scope=all)
&category=<id>
&from=YYYY-MM-DD&to=YYYY-MM-DD   (локальные даты, to включительно)
```

Запись — `router.replace` (смена фильтра не засоряет историю), смена вкладки — тоже `replace`. Перевод в параметры API: `from` → локальная полночь `from` в ISO с часовым поясом, `to` → локальная полночь `to + 1 день`. Некорректные значения в адресе (неизвестная вкладка, мусор в дате) молча отбрасываются.

`EventsView` загружает страницу через `useEventList(params)`: массив `items`, `total`, `loading`, `error`, `loadMore()`, `reload()`. При смене параметров предыдущий запрос игнорируется (счётчик запросов), чтобы поздний ответ старой вкладки не перезаписал новый список.

Компоненты: `EventFilters.vue` (`Select` категории, `DatePicker selectionMode="range"`; на мобильном — кнопка «Фильтры (N)», открывающая `Dialog` во весь экран с теми же полями), `EventListCard.vue`; пустые состояния — в самой `EventsView`. Вкладки — PrimeVue `Tabs` (`TabList`/`Tab` без панелей: содержимое одно, меняются параметры), период — `SelectButton`.

Фильтр «Свободных мест от» — `InputNumber` (1–100, пусто — без фильтра), в адресе `places=N`, в API `min_free_places`.

Выбор дат: `DatePicker` в режиме диапазона после первого клика отдаёт `[день, null]`. Чтобы один клик сразу фильтровал по одному дню, `EventFilters` держит локальное значение календаря: на первый клик сразу отправляет `from = to = день`, но календарь остаётся в состоянии «ждём конец диапазона»; второй клик задаёт конец. При закрытии календаря локальное значение берётся из адреса.

Категории загружаются один раз за сессию в `useCategories()` (модульный кеш промиса).

### Форма мероприятия: одна логика, две раскладки

`useEventForm(getInitial: () => Event | null)` по образцу `useProfileForm`:
- поля: `title`, `categoryId`, `startsAt: Date | null`, `durationMinutes: number | null`, `place`, `maxParticipants` (по умолчанию 10), `minAge` (0), `description`;
- клиентская валидация по правилам спеки, `minParticipants` (для редактирования — `max(2, participants_count)`);
- `submit()` — `POST` для создания, `PATCH` только изменённых полей для редактирования (без изменений — без запроса, как в профиле);
- раскладка ошибок сервера: Pydantic-поля и коды `starts_at_in_past` → `startsAt`, `category_not_found` → `categoryId`, `limit_below_participants` → `maxParticipants`; прочее — общая ошибка.

Общей формы-компонента нет: `CreateEventDialog` раскладывает поля сеткой, а `EventDetails` в режиме редактирования ставит те же поля на места значений (стандарт). Общий — компонент отдельного поля `EventFieldInput.vue` (поле выбирается по имени, форма передаётся через `provide`/`inject` — `eventFormContext.ts`): название, категория (`Select`), дата и время (`DateTimeInput.vue`: на мобильном нативный `datetime-local`, иначе `DatePicker showTime`, по аналогии с `BirthDateInput`), длительность (`InputNumber` в минутах), максимум участников (`InputNumber` с кнопками), возраст (`SelectButton` 0+/14+/16+/18+), описание (`Textarea`).

`CreateEventDialog` реализует правила стандарта модальных окон: `modal`, `dismissableMask` только при `!dirty`, на мобильном `maximizable`-раскладка через класс во весь экран, футер `app-actions app-actions--inline`.

### Страница мероприятия

`EventView` загружает мероприятие (`GET /events/:id`), затем — если `is_joined` или пользователь админ — список участников. Состояние: `event`, `participants`, `notFound`. Все действия после ответа сервера перезапрашивают мероприятие (и список, если он показан): данные о местах важнее экономии запроса.

```text
EventView
 |- EventDetails      просмотр/редактирование на месте (useEventForm)
 |    '- actions      Записаться | Отказаться | Вы организатор
 |                    Редактировать | Удалить (автор/админ, предстоящее)
 '- EventParticipants список + «Исключить» (автор/админ, предстоящее)
```

Права в UI вычисляются из данных: `isOrganizer = event.organizer.id === profile.id`, `canManage = isOrganizer || profile.roles.includes('admin')`, `isPast = new Date(event.starts_at) <= now`, `canJoinAge = profile.age >= event.min_age`. Это только подсказки интерфейса; права проверяет backend.

Подтверждения удаления и исключения — `ConfirmDialog` + `ConfirmationService` (регистрируется в `main.ts`), кнопка подтверждения `severity="danger"`.

Сообщения об ошибках действий — по `detail.code`:

| Код | Текст |
|-----|-------|
| `event_full` | Свободных мест нет |
| `age_restricted` | Мероприятие доступно с N лет |
| `event_started` | Мероприятие уже началось |
| `already_joined` | Вы уже записаны |
| `not_joined` | Вы не записаны на это мероприятие |
| `forbidden` | Недостаточно прав |
| 404 | Мероприятие не найдено |

### Формат даты и времени

`utils/dates.ts` дополняется `formatEventDate(iso, now)` через `Intl.DateTimeFormat('ru', {weekday:'short', day:'numeric', month:'long', hour, minute})` с годом при несовпадении, `toOffsetIso(date)` — локальное время с явным смещением (`2026-11-01T19:00:00+03:00`), `formatDuration(minutes)`; `utils/format.ts` — `formatPlaces`. В тестах часовой пояс фиксируется `TZ=Europe/Moscow` в конфиге Vitest, чтобы проверки формата не зависели от машины.

## Risks / Trade-offs

- [Права в UI вычисляются на клиенте и могут разойтись с сервером] → сервер остаётся источником истины; ответ 403/409 показывается сообщением и страница перезагружает данные.
- [Без стора мероприятий возврат «Назад» перезагружает список и сбрасывает «Показать ещё»] → допустимо для MVP; позиция прокрутки и подгруженные страницы — возможная доработка.
- [Нативный `datetime-local` на мобильном не задаёт часовой пояс] → значение трактуется как локальное время браузера и переводится в ISO со смещением через `toOffsetIso`.
- [Шапка с четырьмя элементами на 360 px] → на мобильном кнопки-иконки по 44 px и логотип без подписи на ширине меньше 380 px; проверяется в браузере на 360 px.

## Migration Plan

Миграций БД нет. Новые параметры `GET /events` необязательные: без них поведение прежнее. Frontend и backend выкатываются вместе через `docker compose`.
