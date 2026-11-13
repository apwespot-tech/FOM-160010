# Design

## Context

Мотивация и рамка описаны в `proposal.md`, требования — в `specs/notifications` и `specs/web-app`.

Что в текущем коде определяет подход:

- Все изменения мероприятия и участия (`update_event`, `delete_event`, `join_event`, `leave_event`, `remove_participant` в `event_service`) выполняются в одной транзакции под `FOR UPDATE` строки мероприятия (`_lock_event`) и завершаются `session.commit()` внутри сервиса. Значит, уведомление, добавленное в ту же сессию до `commit`, атомарно с действием, а одновременные действия над одним мероприятием сериализуются.
- Организатор записан в `event_participants`, как и остальные участники. Поэтому правило «все записанные, кроме совершившего действие» само включает организатора, когда действует администратор, и само исключает организатора, когда действует он.
- `DELETE /events/{id}` удаляет мероприятие безвозвратно, а участники удаляются каскадом. Список получателей нужно прочитать до `session.delete`.
- После `starts_at` состав участников и название не меняются (`event_started`). Поэтому к моменту открытия окна отзывов (`starts_at` + 24 ч) получатели напоминания уже окончательны.
- Фоновых процессов в проекте нет: в `compose.yaml` только `db`, `api` и `web`. Текущее время передаётся параметром `now` (через `NowDep`), что позволяет тестировать границы по времени без ожидания.
- `NotificationsButton` монтируется в `AppHeader` только при `session.isAuthenticated`, в том числе для черновика профиля.

## Goals / Non-Goals

**Goals:**
- Уведомления о действиях не теряются и не появляются для отклонённых действий: та же транзакция, что и действие.
- Напоминания не дублируются при повторных и параллельных прогонах фонового процесса: это гарантирует ограничение БД, а не код.
- Клиент опрашивает сервер лёгкой ручкой, которая сводится к одному индексному `count`.

**Non-Goals:**
- Очередь событий или шина (outbox, pub/sub). Уведомления пишутся прямо в таблицу. Внешней доставки нет, публиковать некуда.
- Общий планировщик задач. `worker` выполняет одну периодическую функцию.
- Поддержка нескольких копий `worker`. Корректность при параллельных прогонах гарантирована, но масштабирование не цель.

## Decisions

### Схема БД: таблица `notifications` (миграция `0008_notifications`)

```
notifications
  id              uuid PK default gen_random_uuid()
  user_id         uuid NOT NULL FK users.id ON DELETE CASCADE      -- получатель
  type            notification_type NOT NULL
                  -- enum: event_changed, event_deleted, participant_removed,
                  --       participant_joined, participant_left, review_reminder
  event_id        uuid NULL FK events.id ON DELETE SET NULL
  event_title     varchar(100) NOT NULL         -- снимок названия на момент создания
  participant_id  uuid NULL FK users.id ON DELETE CASCADE
  changed_fields  varchar(32)[] NULL
  created_at      timestamptz NOT NULL
  read_at         timestamptz NULL
  CHECK ((type IN ('participant_removed','participant_joined','participant_left'))
         = (participant_id IS NOT NULL))
  CHECK ((type = 'event_changed') = (changed_fields IS NOT NULL))
  INDEX ix_notifications_user_created (user_id, created_at DESC, id DESC)
  INDEX ix_notifications_user_unread  (user_id) WHERE read_at IS NULL
  UNIQUE INDEX uq_notifications_review_reminder (user_id, event_id)
         WHERE type = 'review_reminder'
```

- **`event_id ON DELETE SET NULL` и `event_title`** реализуют требование «Уведомления после удаления мероприятия». Так же устроены `reviews`. Уведомление `event_deleted` вставляется до удаления мероприятия, а при удалении его `event_id` обнуляется каскадом.
- **`participant_id ON DELETE CASCADE`.** Удаления пользователей в API нет. Если строку удалят вручную, уведомление о человеке без имени теряет смысл, поэтому оно удаляется вместе с ним. Имя в ответе берётся текущее, через join (см. спеку «Представление уведомления»).
- **`read_at` вместо `boolean read`.** Почти бесплатно и пригодится для отладки. Наружу отдаётся `read = read_at IS NOT NULL`.
- **Частичный уникальный индекс `uq_notifications_review_reminder`** делает напоминание идемпотентным: `worker` вставляет через `INSERT … ON CONFLICT DO NOTHING`. `NULL` в `event_id` не участвует в уникальности. Это допустимо: по удалённому мероприятию новых напоминаний не бывает.
- **Частичный индекс непрочитанных** обслуживает `unread-count`, самую частую ручку: она вызывается раз в 60 секунд от каждой открытой вкладки.
- `changed_fields` — массив имён полей API в фиксированном порядке: `starts_at`, `duration_minutes`, `city_id`, `place`, `title`. Альтернатива — `jsonb` со старыми и новыми значениями. Отклонена: спека требует только перечня, а старые значения потребовали бы форматировать город, длительность и время в нескольких местах.
- `downgrade` удаляет таблицу и enum. Данных для переноса нет.

### Создание уведомлений внутри сервисов мероприятий

Новый модуль `notification_service` с функциями, которые только добавляют объекты в сессию и ничего не коммитят:

```
notify_event_changed(session, now, event, actor, changed_fields)
notify_event_deleted(session, now, event, actor)        # вызывается до session.delete
notify_participant_removed(session, now, event, actor, participant_id)
notify_participant_joined(session, now, event, participant_id)
notify_participant_left(session, now, event, participant_id)
```

`event_service` вызывает их после всех проверок, перед своим `commit`:

```
update_event:  old = {f: getattr(event, f) for f in NOTIFY_FIELDS}
               setattr(...)
               changed = [f for f in NOTIFY_FIELDS if f in fields and old[f] != getattr(event, f)]
               if changed: notify_event_changed(...)
               commit
```

- Получатели читаются запросом `SELECT user_id FROM event_participants WHERE event_id = :id AND user_id <> :actor` под той же блокировкой мероприятия, поэтому состав не может измениться между выборкой и `commit`. Вставка одним `insert().values([...])`.
- `notify_participant_removed`: исключённому, плюс организатору, если `actor.id != event.organizer_id`.
- Ошибка вставки уведомления откатывает всю транзакцию, и действие не выполняется. Это следствие требования «Уведомления вместе с действием». Альтернатива — писать уведомления в отдельной транзакции после `commit` (best-effort). Отклонена: появились бы уведомления о действиях, которые не выполнены, или пропуски.
- `join_event` при `IntegrityError` (`already_joined`) делает `rollback`, и уведомление откатывается вместе с записью.
- Альтернатива — события SQLAlchemy (`after_flush`) или триггеры БД. Отклонены: правило «кто получатель» зависит от того, кто совершил действие, а это есть только в сервисе. Явный вызов легко читать и тестировать.

### Фоновый процесс `worker`

```
 compose
 +-----+   +-------+   +------------------------------+
 | web |-->| api   |-->| db                           |
 +-----+   +-------+   +------------------------------+
                            ^
           +----------------+-------------+
           | worker (образ ./api)         |
           | python -m app.worker         |
           |  loop:                       |
           |    with session:             |
           |      create_review_reminders(session, utc_now())
           |    sleep(WORKER_INTERVAL_SECONDS)
           +------------------------------+
```

- `app/worker.py`: `main()` читает `Settings`, создаёт engine и фабрику сессий так же, как `create_app`, и в бесконечном цикле вызывает `notification_service.create_review_reminders(session, now) -> int`, логируя число созданных напоминаний. Исключение одного прогона логируется, и цикл продолжается. Так переживается и старт раньше, чем `api` применит миграции. `SIGTERM` завершает цикл: `docker compose down` не ждёт таймаута.
- `create_review_reminders` выполняет одну вставку `INSERT … SELECT … ON CONFLICT DO NOTHING`:

```
INSERT INTO notifications (user_id, type, event_id, event_title, created_at)
SELECT p.user_id, 'review_reminder', e.id, e.title, :now
FROM events e JOIN event_participants p ON p.event_id = e.id
WHERE e.starts_at + interval '24 hours' <= :now
  AND e.starts_at + interval '8 days'  >  :now
  AND (SELECT count(*) FROM event_participants q WHERE q.event_id = e.id) >= 2
ON CONFLICT (user_id, event_id) WHERE type = 'review_reminder' DO NOTHING
```

  Константы окна берутся из `review_service` (там они уже определены), а не дублируются. Условие `< starts_at + 8 суток` реализует сценарий «Окно уже закрыто».
- Новая настройка `worker_interval_seconds: int = 300` (`WORKER_INTERVAL_SECONDS`, ≥ 1). Это и есть допустимая задержка из спеки.
- В `compose.yaml` новый сервис `worker`: `build: ./api`, `env_file: .env`, `depends_on: db (healthy), api (started)`, `command: python -m app.worker`, тот же том `./api:/app`. Миграции применяет только `api`, чтобы два процесса не запускали `alembic upgrade` одновременно.
- Альтернативы:
  - **APScheduler в lifespan `api`.** Отклонена: при нескольких воркерах uvicorn задача выполнялась бы в каждом, а будущая внешняя доставка (SMS, push) естественнее в отдельном процессе.
  - **Celery + брокер.** Отклонена как избыточная: нужен новый сервис (Redis), а задача всего одна.
  - **Досоздание при чтении.** Обсуждалась при планировании. Пользователь выбрал фоновый процесс.

### API

| Ручка | Ответ |
|---|---|
| `GET /notifications` | `{"items": [Notification × ≤20], "unread_count": int}` |
| `GET /notifications/unread-count` | `{"unread_count": int}` |
| `POST /notifications/read` `{"up_to": datetime}` | 204 |

- Роутер `notifications` использует `CurrentUser`, а не `CompletedUser`: ручки доступны черновику профиля (спека «Доступ к ручкам уведомлений»). Черновик не может записываться и создавать мероприятия, поэтому уведомлений у него обычно нет, но шапка с колокольчиком у него есть, и опрос не должен получать 403.
- Список — один запрос с `LEFT JOIN users` для `participant.name`, `ORDER BY created_at DESC, id DESC LIMIT 20`. `unread_count` — отдельный `count` по частичному индексу.
- `POST /notifications/read`: `UPDATE notifications SET read_at = :now WHERE user_id = :me AND read_at IS NULL AND created_at <= :up_to`. Повторный вызов ничего не меняет и тоже отвечает 204. `up_to` без часового пояса отклоняется с 422 по общему правилу схем, как `starts_at`.
- **Почему `up_to`, а не «прочитать всё».** Уведомление, пришедшее между `GET` и отметкой, иначе станет прочитанным, хотя пользователь его не видел (спека, сценарий «Уведомление пришло после показа»). Альтернатива — передавать список `id`. Отклонена: граница по времени проще и даёт тот же результат.

### Frontend

- `web/src/api/notifications.ts`: типы `Notification`, `NotificationType` и функции `listNotifications`, `getUnreadCount`, `markRead(upTo)`.
- `web/src/composables/useUnreadNotifications.ts`: `unreadCount` и `refresh()`. Запрос при монтировании, `setInterval` на 60 с с пропуском, пока `document.visibilityState !== 'visible'`, и запрос по `visibilitychange` → `visible`. Таймер и слушатель снимаются в `onUnmounted`. `NotificationsButton` размонтируется при выходе, поэтому отдельная логика остановки по `logout` не нужна. Ошибки запроса глотаются, значение остаётся прежним.
- `NotificationsButton.vue`:
  - точка поверх иконки — `OverlayBadge` PrimeVue, или своя точка, если `OverlayBadge` в 4.5 не позволяет показывать её без числа;
  - `aria-label` меняется по наличию непрочитанных;
  - при открытии `Popover`: `listNotifications()`, затем `markRead(items[0].created_at)`, если список не пуст, и `unreadCount = 0` локально;
  - выделение рисуется по полю `read` из полученного ответа и не меняется до закрытия;
  - при повторном открытии список загружается заново;
  - список с `max-height` и прокруткой внутри панели;
  - элемент с `event.id` — `RouterLink` на `/events/:id`, который закрывает панель; без `event.id` — обычный блок.
- Тексты — чистая функция `notificationText(n, currentUserId)` в `web/src/utils/`: её легко покрыть таблицей тестов.

## Risks / Trade-offs

- **Записи, вставленные с более ранним `created_at`, чем `up_to`.** `created_at` = `now` начала запроса, а `commit` может случиться позже. Если клиент получил список между `now` и `commit` чужого действия, такое уведомление при отметке может стать прочитанным, не будучи показанным. → Окно — миллисекунды. Уведомление останется в списке, его увидят при следующем открытии панели. Для внутренних уведомлений это допустимо.
- **Рост таблицы без очистки.** → Индексы по `user_id` держат чтение быстрым при любом объёме истории. Очистка вынесена в бэклог.
- **Опрос раз в 60 секунд от каждой видимой вкладки.** → Ручка сводится к индексному `count`. При росте нагрузки интервал можно поднять, не меняя API.
- **`worker` упал или не запущен.** Напоминания не создаются, а остальные уведомления работают: их создаёт `api`. → Ошибки прогона логируются, `restart: unless-stopped` у сервиса. Если `worker` отставал меньше 7 суток, пропущенные напоминания досоздадутся при следующем прогоне.
- **Ошибка вставки уведомления блокирует основное действие.** → Вставка простая, в те же таблицы БД, без внешних вызовов. Отказ вероятен только вместе с отказом самой БД.
- **Напоминания по старым мероприятиям при первом запуске** (в том числе из `seed_demo_events.py`): мероприятия, у которых окно отзывов открыто сейчас, получат напоминание сразу. → Это ожидаемое поведение по спеке, отдельная миграция данных не нужна.

## Migration Plan

1. Миграция `0008_notifications` применяется при старте `api` (`alembic upgrade head`).
2. `docker compose up --build` поднимает новый сервис `worker`. До завершения миграции его прогоны падают с ошибкой и повторяются.
3. Откат: остановить `worker`, затем `alembic downgrade 0007` и откат кода. Уведомления теряются, остальные данные не затрагиваются.
