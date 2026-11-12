# Картинки категорий

Картинки по умолчанию для категорий мероприятий: сплошной фон и белый значок категории, 1200×675, WebP. Их загружает миграция `0004_catalog_covers`; имя файла — slug категории.

| Файл | Категория | Значок | Фон |
|---|---|---|---|
| `board-games.webp` | Настольные игры | `pi-th-large` | `#7c3aed` |
| `walks.webp` | Прогулки | `pi-map` | `#16a34a` |
| `sport.webp` | Спорт | `pi-bolt` | `#ea580c` |
| `cinema.webp` | Кино | `pi-video` | `#475569` |

Значки — глифы шрифта [PrimeIcons](https://github.com/primefaces/primeicons) (лицензия MIT), тот же набор иконок, что во frontend.

## Пересборка

Генератор детерминирован: при той же версии Pillow и PrimeIcons файлы совпадают байт в байт. Шрифт берётся из `web/node_modules` (после `npm install` во `web/`):

```bash
docker compose run --rm -v "$(pwd)/web/node_modules/primeicons:/primeicons:ro" api \
  python scripts/generate_category_covers.py \
  --font /primeicons/fonts/primeicons.ttf --css /primeicons/primeicons.css \
  --out migrations/assets/category_covers
```

Новая категория добавляется в `COVERS` генератора и в миграцию вместе с картинкой: без картинки категорию сохранить нельзя.
