"""Демо-данные для стенда: организаторы, участники и 50 разных мероприятий.

Скрипт работает только через публичный API, поэтому подходит для любого стенда:
локального или удалённого. На стенде должны быть включены тестовые ручки входа
(`AUTH_TEST_ENDPOINTS=true`): код входа скрипт берёт из `GET /api/auth/test/code`.

Запуск (нужен только Python 3.11+, Pillow — для фото, необязательно):

    python api/scripts/seed_demo_events.py --base-url http://localhost:8000
    python api/scripts/seed_demo_events.py --base-url https://staging.example.ru --photos

Повторный запуск не создаёт дублей: если у демо-организаторов уже есть мероприятия,
скрипт останавливается. `--reset` сначала удаляет их предстоящие мероприятия и создаёт
партию заново, `--force` добавляет ещё одну партию к существующей.
"""

from __future__ import annotations

import argparse
import io
import json
import random
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

# Номера демо-пользователей: +7 999 700-00-XX — не пересекаются с реальными
ORGANIZERS = [
    ("+79997000001", "Анна Смирнова", "@anna_demo", "Организую настолки и прогулки по выходным."),
    ("+79997000002", "Дмитрий Козлов", "@dima_demo", "Бегаю, катаюсь, зову с собой."),
    ("+79997000003", "Мария Волкова", "@masha_demo", "Люблю кино и долгие разговоры после."),
    ("+79997000004", "Игорь Новиков", "@igor_demo", "Спорт по утрам, игры по вечерам."),
    ("+79997000005", "Екатерина Орлова", "@katya_demo", "Ищу компанию для всего интересного."),
]
PARTICIPANTS = [
    ("+79997000011", "Олег Петров"),
    ("+79997000012", "Светлана Иванова"),
    ("+79997000013", "Никита Соколов"),
    ("+79997000014", "Алина Морозова"),
    ("+79997000015", "Павел Лебедев"),
    ("+79997000016", "Юлия Кузнецова"),
]
# Москва чаще остальных: на стенде так выглядит живой каталог
CITY_WEIGHTS = {
    "Москва": 8,
    "Санкт-Петербург": 4,
    "Казань": 2,
    "Екатеринбург": 2,
    "Новосибирск": 1,
    "Нижний Новгород": 1,
}

# Заготовки по названию категории: (название, описание, место)
TEMPLATES: dict[str, list[tuple[str, str, str]]] = {
    "Настольные игры": [
        (
            "Вечер «Каркассона»",
            "Играем пару партий, новичкам всё объясним.",
            "Антикафе «Циферблат»",
        ),
        (
            "Мафия на 10 человек",
            "Классическая мафия с ведущим. Приходите вовремя.",
            "Клуб «Игротека»",
        ),
        ("Кодовые имена и Диксит", "Лёгкие игры для компании, можно без опыта.", "Кафе «Пешка»"),
        ("Турнир по «Каталонии»", "Три тура, победителю — шоколадка.", "Антикафе «Время есть»"),
        (
            "Евроигры для опытных",
            "«Брасс» и «Терраформирование Марса». Партии долгие.",
            "Клуб «Мипл»",
        ),
        (
            "Настолки для новичков",
            "Простые игры, чтобы познакомиться.",
            "Библиотека им. Лермонтова",
        ),
    ],
    "Прогулки": [
        (
            "Прогулка по старому центру",
            "Неспешно, с остановками на кофе.",
            "Сбор у главного входа в парк",
        ),
        ("Вечерняя набережная", "Гуляем вдоль реки, фотографируем закат.", "Набережная, у моста"),
        ("Экскурсия по дворам", "Покажу необычные дворы и арки.", "Метро «Чистые пруды»"),
        ("Поход выходного дня", "12 км по лесу, взять воду и удобную обувь.", "Станция электрички"),
        ("Прогулка с собаками", "Берите питомцев, будет весело.", "Парк, центральная поляна"),
        (
            "Утренний ботанический сад",
            "Смотрим оранжереи и цветущие аллеи.",
            "Ботанический сад, касса",
        ),
    ],
    "Спорт": [
        (
            "Утренняя пробежка 5 км",
            "Темп спокойный, никого не бросаем.",
            "Парк Горького, вход со стороны набережной",
        ),
        ("Волейбол в зале", "Играем 3 часа, зал оплачен, скидываемся.", "Спортзал школы № 57"),
        ("Велопрогулка 30 км", "Маршрут по паркам, шлем обязателен.", "Сбор у прокатной станции"),
        ("Йога на траве", "Коврики свои, уровень любой.", "Парк, у фонтана"),
        ("Футбол 5×5", "Ищем ещё игроков на две команды.", "Мини-поле у стадиона"),
        ("Скалодром для начинающих", "Инструктор покажет основы.", "Скалодром «Вертикаль»"),
    ],
    "Кино": [
        ("Новинка в IMAX", "Идём на вечерний сеанс, потом обсуждаем.", "Кинотеатр «Октябрь»"),
        ("Киноклуб: советская классика", "Смотрим и разбираем фильм.", "Лекторий «Дом кино»"),
        ("Фильм под открытым небом", "Пледы и термосы приветствуются.", "Летний кинотеатр в парке"),
        ("Марафон фильмов Нолана", "Две картины подряд с перерывом.", "Антикафе «Кинозал»"),
        ("Артхаус и разговоры", "Небольшой зал, после сеанса — кафе.", "Кинотеатр «Пионер»"),
        ("Мультфильмы для взрослых", "Ностальгия и попкорн.", "Кинотеатр «Ролан»"),
    ],
}
GENERIC = [
    ("Встреча по интересам", "Знакомимся и решаем, чем займёмся дальше.", "Кафе в центре"),
    ("Мастер-класс", "Всё необходимое выдадут на месте.", "Лофт-пространство"),
    ("Вечер знакомств", "Неформальная встреча в спокойной обстановке.", "Антикафе"),
]
MOSCOW = timezone(timedelta(hours=3))
DURATIONS = [60, 90, 120, 120, 150, 180, 240, None]
MIN_AGES = [0, 0, 0, 0, 14, 16, 18]
# Цвета фото без градиентов: сплошной фон и надпись
PHOTO_COLORS = ["#7c3aed", "#0f766e", "#b45309", "#be123c", "#1d4ed8", "#15803d", "#4338ca"]


class ApiError(RuntimeError):
    def __init__(self, status: int, body: Any) -> None:
        super().__init__(f"HTTP {status}: {body}")
        self.status = status
        self.body = body


@dataclass
class Client:
    base: str
    context: ssl.SSLContext | None

    def call(
        self,
        method: str,
        path: str,
        body: Any = None,
        token: str | None = None,
        *,
        form: tuple[bytes, str] | None = None,
    ) -> Any:
        headers = {"Accept": "application/json"}
        data: bytes | None = None
        if form is not None:
            data, content_type = form
            headers["Content-Type"] = content_type
        elif body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(
            self.base + "/api" + path, data=data, method=method, headers=headers
        )
        try:
            with urllib.request.urlopen(request, context=self.context, timeout=30) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            raw = error.read()
            try:
                parsed = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                parsed = raw.decode(errors="replace")[:200]
            raise ApiError(error.code, parsed) from None

    def login(self, phone: str) -> str:
        """Вход по тестовому коду; при паузе между запросами кода ждёт и повторяет."""
        while True:
            try:
                self.call("POST", "/auth/code", {"phone": phone})
                break
            except ApiError as error:
                if error.status != 429:
                    raise
                wait = int((error.body or {}).get("detail", {}).get("retry_after", 60)) + 1
                print(f"  пауза запроса кода для {phone}: ждём {wait} с")
                time.sleep(wait)
        try:
            code = self.call("GET", "/auth/test/code?" + urllib.parse.urlencode({"phone": phone}))
        except ApiError as error:
            if error.status == 404:
                sys.exit("Тестовые ручки входа выключены на стенде: нужна AUTH_TEST_ENDPOINTS=true")
            raise
        tokens = self.call("POST", "/auth/verify", {"phone": phone, "code": code["code"]})
        return str(tokens["access_token"])


# Шрифты с кириллицей: Linux, Windows, macOS
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]


def find_font(explicit: str | None) -> str | None:
    """Путь к шрифту для надписи на фото: из --font или первый найденный из списка."""
    from pathlib import Path

    for candidate in [explicit] if explicit else FONT_CANDIDATES:
        if candidate and Path(candidate).is_file():
            return candidate
    return None


def build_photo(title: str, color: str, font_path: str) -> bytes:
    """JPEG 1200×800: сплошной фон и название мероприятия белым."""
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (1200, 800), color)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_path, 72)
    words, lines, line = title.split(), [], ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if draw.textlength(candidate, font=font) > 1000 and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    lines.append(line)
    y = 400 - len(lines) * 45
    for text in lines:
        width = draw.textlength(text, font=font)
        draw.text(((1200 - width) / 2, y), text, fill="white", font=font)
        y += 90
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=85)
    return buffer.getvalue()


def multipart(order: list[dict[str, int]], photo: bytes) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="order"\r\n\r\n'.encode()
        + json.dumps(order).encode()
        + b"\r\n",
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="files"; '
            f'filename="demo.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'
        ).encode()
        + photo
        + b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def prepare_user(client: Client, phone: str, name: str, city_id: int, **extra: Any) -> str:
    token = client.login(phone)
    client.call(
        "PATCH",
        "/profile",
        {"name": name, "birth_date": "1994-06-15", "city_id": city_id, **extra},
        token,
    )
    return token


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--base-url", required=True, help="адрес стенда, например http://localhost:8000"
    )
    parser.add_argument("--count", type=int, default=50, help="сколько мероприятий создать")
    parser.add_argument("--photos", action="store_true", help="приложить к части мероприятий фото")
    parser.add_argument("--font", help="TTF-шрифт с кириллицей для надписей на фото")
    parser.add_argument(
        "--reset", action="store_true", help="удалить предстоящие демо-мероприятия и создать заново"
    )
    parser.add_argument("--force", action="store_true", help="создать, даже если демо уже есть")
    parser.add_argument("--insecure", action="store_true", help="не проверять HTTPS-сертификат")
    parser.add_argument("--seed", type=int, default=42, help="зерно случайных данных")
    args = parser.parse_args()

    context = ssl._create_unverified_context() if args.insecure else None  # noqa: S323
    client = Client(args.base_url.rstrip("/"), context)
    rng = random.Random(args.seed)

    print(f"Стенд: {client.base}")
    font_path = None
    if args.photos:
        try:
            import PIL  # noqa: F401
        except ImportError:
            print("Pillow не установлен — мероприятия будут без фото (pip install pillow)")
        else:
            font_path = find_font(args.font)
            if font_path is None:
                print("Не найден шрифт с кириллицей — мероприятия будут без фото (укажите --font)")
    first_token = client.login(ORGANIZERS[0][0])
    cities = {city["name"]: city["id"] for city in client.call("GET", "/cities", token=first_token)}
    categories = client.call("GET", "/categories", token=first_token)
    city_pool = [
        name for name, weight in CITY_WEIGHTS.items() if name in cities for _ in range(weight)
    ]
    if not city_pool:
        city_pool = list(cities)
    moscow = cities.get("Москва", next(iter(cities.values())))

    print("Организаторы:")
    organizers = []
    for phone, name, telegram, about in ORGANIZERS:
        token = prepare_user(client, phone, name, moscow, telegram=telegram, about=about)
        existing = client.call("GET", "/events?scope=organized&limit=100", token=token)
        organizers.append(token)
        removed = 0
        if args.reset:
            for event in existing["items"]:
                client.call("DELETE", f"/events/{event['id']}", token=token)
                removed += 1
        print(f"  {name} ({phone}), мероприятий: {existing['total']}, удалено: {removed}")
        if existing["total"] and not args.reset and not args.force:
            sys.exit("Демо-мероприятия уже созданы. --reset пересоздаст их, --force добавит ещё.")

    print("Участники:")
    participants = []
    for phone, name in PARTICIPANTS:
        participants.append(prepare_user(client, phone, name, moscow))
        print(f"  {name} ({phone})")

    # Равномерно по категориям, внутри категории — разные заготовки
    pools = {
        category["id"]: list(TEMPLATES.get(category["name"], GENERIC)) for category in categories
    }
    # Время мероприятий — по Москве: вечерние встречи и утренний спорт
    now = datetime.now(MOSCOW)
    created = 0
    with_photos = 0
    for index in range(args.count):
        category = categories[index % len(categories)]
        pool = pools[category["id"]]
        title, description, place = pool[(index // len(categories)) % len(pool)]
        city_name = rng.choice(city_pool)
        day = now + timedelta(days=rng.randint(1, 30))
        starts_at = day.replace(
            hour=rng.choice([10, 12, 18, 19, 20]),
            minute=rng.choice([0, 30]),
            second=0,
            microsecond=0,
        )
        max_participants = rng.choice([4, 6, 8, 10, 12, 16, 20])
        organizer = organizers[index % len(organizers)]
        event = client.call(
            "POST",
            "/events",
            {
                "title": title[:100],
                "description": description,
                "place": place,
                "starts_at": starts_at.isoformat(),
                "duration_minutes": rng.choice(DURATIONS),
                "category_id": category["id"],
                "city_id": cities[city_name],
                "max_participants": max_participants,
                "min_age": rng.choice(MIN_AGES),
            },
            organizer,
        )
        # Несколько участников: у карточек разное число свободных мест
        joined = 0
        wanted = rng.randint(0, min(len(participants), max_participants - 1))
        for token in rng.sample(participants, k=wanted):
            try:
                client.call("POST", f"/events/{event['id']}/join", token=token)
                joined += 1
            except ApiError as error:
                # Возрастное ограничение или нехватка мест — просто пропускаем
                if error.status not in (403, 409):
                    raise
        if font_path and index % 2 == 0:
            photo = build_photo(title, PHOTO_COLORS[index % len(PHOTO_COLORS)], font_path)
            client.call(
                "PUT",
                f"/events/{event['id']}/photos",
                token=organizer,
                form=multipart([{"file": 0}], photo),
            )
            with_photos += 1
        created += 1
        print(f"  [{created:2}/{args.count}] {title} — {city_name}, {category['name']}, +{joined}")

    print(f"Готово: {created} мероприятий, с фото: {with_photos}.")
    print(f"Войти и посмотреть: {ORGANIZERS[0][1]}, телефон {ORGANIZERS[0][0]}.")


if __name__ == "__main__":
    try:
        main()
    except ApiError as error:
        sys.exit(f"Ошибка API: {error}")
    except urllib.error.URLError as error:
        sys.exit(f"Стенд недоступен: {error.reason}")
