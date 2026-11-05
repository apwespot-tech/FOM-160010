"""Генератор картинок категорий: сплошной фон и белый значок primeicons по центру.

Картинки нужны только миграциям (готовые файлы лежат в migrations/assets/category_covers),
в рантайме приложения скрипт не используется. Пересборка — см. README рядом с картинками.
"""

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1200, 675
GLYPH_SIZE = 280  # ~40% высоты картинки
QUALITY = 85


@dataclass(frozen=True)
class CategoryCover:
    slug: str
    icon: str
    color: str


# Должно совпадать с миграцией 0004: имя файла — slug, значок — поле icon категории
COVERS = (
    CategoryCover("board-games", "pi-th-large", "#7c3aed"),
    CategoryCover("walks", "pi-map", "#16a34a"),
    CategoryCover("sport", "pi-bolt", "#ea580c"),
    CategoryCover("cinema", "pi-video", "#475569"),
)


def glyph_codes(css: str) -> dict[str, str]:
    """Имя иконки -> символ глифа из primeicons.css (`.pi-video:before { content: "\\e962"; }`)."""
    pattern = re.compile(r"\.(pi-[a-z0-9-]+):before\s*\{\s*content:\s*\"\\([0-9a-f]+)\"", re.I)
    return {name: chr(int(code, 16)) for name, code in pattern.findall(css)}


def render(cover: CategoryCover, font: ImageFont.FreeTypeFont, glyph: str) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), cover.color)
    draw = ImageDraw.Draw(image)
    # anchor="mm" — центр глифа точно в центре картинки
    draw.text((WIDTH / 2, HEIGHT / 2), glyph, font=font, fill="#ffffff", anchor="mm")
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", required=True, type=Path, help="primeicons.ttf")
    parser.add_argument("--css", required=True, type=Path, help="primeicons.css")
    parser.add_argument("--out", required=True, type=Path, help="каталог для .webp")
    args = parser.parse_args()

    codes = glyph_codes(args.css.read_text(encoding="utf-8"))
    font = ImageFont.truetype(str(args.font), GLYPH_SIZE)
    args.out.mkdir(parents=True, exist_ok=True)
    for cover in COVERS:
        if cover.icon not in codes:
            raise SystemExit(f"В primeicons нет иконки {cover.icon}")
        path = args.out / f"{cover.slug}.webp"
        render(cover, font, codes[cover.icon]).save(path, format="WEBP", quality=QUALITY)
        print(f"{path} ({path.stat().st_size} байт)")


if __name__ == "__main__":
    main()
