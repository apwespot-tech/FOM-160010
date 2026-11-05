# Tasks

## 1. Backend: фильтр по городу в каталоге

- [x] 1.1 Параметр `city_id: int | None` в `GET /events` (`app/routers/events.py`) и в `event_service.list_events`: проверка `_ensure_city_exists` (422 `city_not_found`) и условие `Event.city_id == city_id`. Проверить тестами в `tests/test_events_catalog.py` все сценарии «Фильтр по городу»: только мероприятия Казани и `total`, без параметра — все города, вместе с `category_id` и `min_free_places`, `scope=joined&period=past`, город без мероприятий — пустой список, `city_id=999999` → 422 `city_not_found`, `city_id=abc` → 422.
- [x] 1.2 Проверить backend целиком: `docker compose exec api pytest` и `docker compose exec api sh -c "ruff check . && ruff format --check . && mypy"` проходят.

## 2. Frontend: состояние списка

- [x] 2.1 `cityId` в `EventListState`: `parseListQuery` (`city` — положительное целое, иначе `null`), `buildListQuery` (`city`), `toListParams` (`city_id` на всех вкладках), `activeFilters` учитывает город, `resetFilters` его очищает. Проверить тестами в `tests/events-list.spec.ts` («Состояние списка в адресе»): `?city=5` → `cityId` = 5 и `city_id: 5` в параметрах для `find`, `joined` и `organized`; `?city=abc` и `?city=0` → `null`; `buildListQuery` пишет и не пишет `city`; город входит в счётчик активных.

## 3. Frontend: поле «Город»

- [x] 3.1 Поле «Город» в `EventFilters.vue` вторым после поиска (на мобильном — первым в окне «Фильтры»): `Select` с `filter`, вариантами «Все города» → город профиля с подписью «ваш город» → остальные по алфавиту без повтора; передача `cityId` из `EventsView.vue`; от 1024 px поиск отдельной строкой, под ним четыре поля. Проверить тестами в `tests/events-list.spec.ts` все сценарии «Фильтр по городу в списке»: по умолчанию «Все города» и запрос без `city_id`, порядок вариантов с городом профиля и без него, выбор города и возврат ко всем городам (адрес и запрос), поиск «каз», сохранение города при переходе на «Участвую», ссылка `/?tab=organized&city=…`, `/?city=abc`.
- [x] 3.2 Обновить сценарии «Фильтры и состояние списка» в `tests/events-list.spec.ts`: «Сбросить» очищает и город; на 360 px с городом, категорией и местами кнопка показывает «Фильтры (3)», а поле «Город» есть в окне «Фильтры». Проверить: тесты проходят.
- [x] 3.3 Проверить frontend целиком: `npm run lint`, `npm run format:check`, `npm run typecheck` и `npm test` в `web/` проходят; вручную на 360, 768, 1024 и 1280 px панель фильтров без горизонтальной прокрутки, плейсхолдеры полей не обрезаются.

## 4. Документация

- [x] 4.1 Удалить пункт «Фильтр каталога по городу» из `docs/backlog.md`. Проверить: пункта нет, `openspec validate add-city-filter --strict` проходит.

## Workflow follow-up

- После ревью — `/opsx:archive` для переноса дельт в основные спеки.
