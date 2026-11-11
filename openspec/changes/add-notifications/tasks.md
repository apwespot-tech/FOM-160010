# Tasks

## 1. Backend: модель и миграция

- [x] 1.1 Модель `Notification` и enum `NotificationType` в `app/models/notification.py` (экспорт в `app/models/__init__.py`) по design: поля, `event_id` с `ON DELETE SET NULL`, `participant_id` и `user_id` с `ON DELETE CASCADE`, два `CHECK`, индекс `(user_id, created_at DESC, id DESC)`, частичный индекс непрочитанных, частичный уникальный индекс `uq_notifications_review_reminder`. Миграция `0008_notifications` (enum, таблица, индексы; `downgrade` удаляет их). Проверить: `test_migrations.py` проходит upgrade/downgrade до `0007` и обратно; в `test_db_constraints.py` — `participant_joined` без `participant_id` отклоняется БД, `event_changed` без `changed_fields` отклоняется, второе `review_reminder` той же пары отклоняется, после удаления мероприятия у уведомления `event_id IS NULL` и прежний `event_title`.

## 2. Backend: уведомления о действиях с мероприятием

- [x] 2.1 `notification_service`: функции `notify_*` из design, которые добавляют строки в сессию без `commit`; выборка получателей «записанные, кроме совершившего действие». Проверить: вызовы через сервисы в задачах 2.2–2.4 покрывают каждую функцию.
- [x] 2.2 `update_event`: сравнение `starts_at`, `duration_minutes`, `city_id`, `place`, `title` до и после, `notify_event_changed` при непустом списке. `delete_event`: `notify_event_deleted` до `session.delete`. Проверить в новом `tests/test_notifications.py` все сценарии «Уведомление об изменении мероприятия» (перенос времени и места, только описание и лимит, прежнее значение, название, администратор, отклонение с `limit_below_participants`, мероприятие без других участников) и «Уведомление об удалении мероприятия» (организатор, администратор, `event_started`).
- [x] 2.3 `remove_participant`: уведомление исключённому и организатору, если действует не он. Проверить сценарии «Уведомление об исключении участника»: организатор, администратор, `participant_not_found`.
- [x] 2.4 `join_event` и `leave_event`: `participant_joined` и `participant_left` организатору. Проверить сценарии «Уведомления организатору о записи и отказе»: запись, запись и отказ подряд, `event_full`. Отдельно — тест гонки (по образцу `test_dictionary_races.py`): два одновременных `join` на последнее место дают одно `participant_joined`.
- [x] 2.5 Атомарность: тест «Сбой при сохранении» в `test_notifications.py`. Ошибка при `commit` записи (например, подменённый `flush`, бросающий `IntegrityError`) не оставляет ни записи, ни уведомления. Проверить: тест проходит, существующие `test_events_*.py` не сломаны.

## 3. Backend: API уведомлений

- [x] 3.1 Схемы `app/schemas/notification.py`: `NotificationOut` (`event`, `participant`, `changed_fields`, `read`), `NotificationList`, `UnreadCount`, `MarkRead` (`up_to` — datetime с часовым поясом, `extra="forbid"`). Проверить: в `test_notifications.py` «Без up_to» → 422, `up_to` без часового пояса → 422.
- [x] 3.2 Роутер `app/routers/notifications.py` на `CurrentUser`: `GET /notifications`, `GET /notifications/unread-count`, `POST /notifications/read`; подключить в `main.py`. Проверить сценарии «Представление уведомления», «Уведомления после удаления мероприятия», «Список уведомлений» (25 → 20 и `unread_count` = 22, ровно 20, пусто, администратор видит только свои), «Число непрочитанных», «Отметка уведомлений прочитанными» (отметка показанных, уведомление после показа остаётся непрочитанным, повторная отметка).
- [x] 3.3 Доступ: без токена → 401 на всех трёх ручках, черновик профиля → 200. Проверить: тесты «Доступ к ручкам уведомлений»; реестр в `test_access_profile_incomplete.py` дополнен ручками уведомлений как доступными черновику.

## 4. Backend: фоновый процесс

- [x] 4.1 `notification_service.create_review_reminders(session, now) -> int`: `INSERT … SELECT … ON CONFLICT DO NOTHING` по design, границы окна — константы `REVIEWS_OPEN_AFTER` и `REVIEWS_CLOSE_AFTER` из `review_service`. Проверить в `test_notifications.py` сценарии «Напоминание об окне отзывов»: окно открылось (трое получили по одному), за минуту до открытия — ничего, ровно в момент открытия — создаются, повторный прогон — без дублей, единственный участник — ничего, ровно в `starts_at` + 8 суток — ничего. Плюс тест одновременных прогонов в двух сессиях: по одному напоминанию у каждого.
- [x] 4.2 Настройка `worker_interval_seconds` (≥ 1, по умолчанию 300) в `Settings`, модуль `app/worker.py`: цикл с `sleep`, исключение прогона логируется и не останавливает цикл, `SIGTERM` завершает цикл. Проверить: unit-тест в `test_unit.py` — один шаг цикла вызывает `create_review_reminders` с текущим временем и переживает исключение; `docker compose run --rm api python -c "import app.worker"` выполняется без ошибок.
- [x] 4.3 Сервис `worker` в `compose.yaml` (`build: ./api`, `env_file`, `depends_on` db healthy и api started, `command: python -m app.worker`, `restart: unless-stopped`, том `./api:/app`), `WORKER_INTERVAL_SECONDS` в `.env.example`. Проверить: `docker compose up --build` поднимает `worker`, в логах `docker compose logs worker` видно число созданных напоминаний за прогон.
- [x] 4.4 Документация: `docs/architecture.md` (схема сервисов с `worker`, `app/worker.py` и новые модули в структуре, раздел о создании уведомлений в транзакции действия), `README.md` (сервис `worker`, переменная интервала). Проверить: команды и пути в README совпадают с `compose.yaml`.
- [x] 4.5 Проверить backend целиком: `docker compose run --rm api pytest` и `docker compose run --rm api sh -c "ruff check . && ruff format --check . && mypy"` проходят.

## 5. Frontend: API и тексты

- [x] 5.1 `web/src/api/notifications.ts`: типы `Notification`, `NotificationType` и функции `listNotifications`, `getUnreadCount`, `markRead(upTo)`. Проверить: новый `tests/api-notifications.spec.ts` — методы, URL и тело `{"up_to": …}`.
- [x] 5.2 `notificationText(n, currentUserId)` в `web/src/utils/`. Проверить: тесты в `tests/notification-text.spec.ts` по сценариям «Тексты уведомлений» — все шесть типов, порядок полей «время, место» при `changed_fields` = `["place", "starts_at"]`, оба варианта `participant_removed`.

## 6. Frontend: колокольчик

- [x] 6.1 Composable `useUnreadNotifications`: запрос при монтировании, раз в 60 с только при видимой вкладке, сразу при `visibilitychange` → `visible`, снятие таймера и слушателя при размонтировании, ошибки не меняют значение. Проверить: новый `tests/notifications.spec.ts` с fake timers — сценарии «Отметка непрочитанных уведомлений»: периодическое обновление, скрытая вкладка, выход (после размонтирования запросов нет), ошибка запроса.
- [x] 6.2 `NotificationsButton.vue`: точка без числа при `unread_count` > 0, `aria-label` «Уведомления, есть непрочитанные». В панели — загрузка списка при открытии, выделение непрочитанных, «Уведомлений пока нет», «Не удалось загрузить уведомления», `markRead` с `created_at` самого нового и сброс точки, переход по клику с закрытием панели, некликабельное удалённое мероприятие, прокрутка внутри панели. Стили — по разделу «UI» в `docs/rules.md`. Проверить в `notifications.spec.ts` сценарии «Уведомления» и «Прочтение уведомлений при открытии панели»; в `header.spec.ts` обновлён сценарий «Шапка на компьютере» и удалена проверка «запросов к серверу нет».
- [x] 6.3 Проверить frontend целиком: `docker compose run --rm web npm test` и `docker compose run --rm web sh -c "npm run lint && npm run format:check && npm run typecheck"` проходят.

## 7. Интеграция и бэклог

- [x] 7.1 Ручная проверка в `docker compose up --build`, двумя пользователями: запись второго пользователя → у организатора появляется точка в течение 60 с, открытие панели снимает её, клик открывает мероприятие; перенос времени организатором → уведомление «Изменилось мероприятие «…»: время» у участника; удаление → некликабельное уведомление; на ширине 360 px панель без горизонтальной прокрутки. Напоминание проверяется на прошедшем мероприятии из `api/scripts/seed_demo_events.py` после прогона `worker`.
- [x] 7.2 `docs/backlog.md`: удалить пункты «уведомления участников об изменении, удалении и исключении», «отметка непрочитанных уведомлений на колокольчике», «уведомления и напоминания «оцените участников»»; добавить вынесенное за рамки (второе напоминание, свёртка записи и отказа, уведомления о прочих полях и участники, переставшие подходить по возрасту, внешняя доставка и realtime, удаление и настройки уведомлений, очистка старых, страница всех уведомлений, счётчик на кнопке). Проверить: в бэклоге нет реализованных пунктов.

## Workflow follow-up

- После ревью архивировать изменение (`/opsx:archive`) и синхронизировать спеки `notifications` и `web-app`.
