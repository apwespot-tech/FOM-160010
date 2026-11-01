# Сайт репетитора по информатике (ОГЭ)

Одностраничный сайт-визитка репетитора: о себе, программа подготовки к ОГЭ,
формат и цены, FAQ и форма заявки. Заявки из формы попадают в Google Таблицу
через Google Apps Script.

## Стек

| Часть | Технология |
|---|---|
| Сайт | HTML + CSS + JavaScript (без сборки), шрифты Google Fonts |
| Приём заявок | Google Apps Script → Google Таблица |
| Локальный сервер | Docker + nginx (или Python `http.server`) |
| Редактор | VS Code (рекомендованные расширения в `.vscode/extensions.json`) |

## Структура

```text
tutor-site/
├── web/                  ← то, что видит посетитель
│   ├── index.html
│   └── images/
├── apps-script/          ← код приёма заявок (вставляется в Google Apps Script)
├── docs/                 ← стандарт оформления и инструкция по форме
├── Dockerfile            ← образ nginx с сайтом
├── nginx.conf
├── compose.yaml
└── .env.example          ← пример настроек (порт)
```

## Рабочее окружение

Нужно установить:

- [Git](https://git-scm.com/downloads) — `git --version`
- [VS Code](https://code.visualstudio.com/) — при открытии папки предложит рекомендованные расширения
- **Один из вариантов** для локального запуска:
  - [Docker Desktop](https://www.docker.com/products/docker-desktop/) — `docker compose version`
  - или [Python 3](https://www.python.org/downloads/) — `python --version`

## Запуск

### Вариант 1. Docker (как на сервере)

```bash
cd tutor-site
cp .env.example .env        # при необходимости поменять WEB_PORT
docker compose up --build -d
```

Сайт: <http://localhost:8080>, проверка работоспособности: <http://localhost:8080/healthz>.

Автообновление при правке файлов в `web/`:

```bash
docker compose watch
```

Остановить: `docker compose down`.

### Вариант 2. Python (без Docker)

```bash
cd tutor-site/web
python -m http.server 8080 --bind 127.0.0.1
```

Сайт: <http://localhost:8080>.

### Вариант 3. VS Code Live Server

Откройте папку `tutor-site` в VS Code и нажмите **Go Live** в строке состояния —
корень сервера уже настроен на `web/`.

## Форма заявок

Как подключить форму к своей Google Таблице — в [docs/ИНСТРУКЦИЯ-ФОРМА.md](docs/ИНСТРУКЦИЯ-ФОРМА.md).
Адрес веб-приложения хранится в `web/index.html` в константе `SCRIPT_URL`.
Это публичный адрес для отправки формы, а не секрет, но пароли и токены в репозиторий
не добавляются.
