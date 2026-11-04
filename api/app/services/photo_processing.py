"""Проверка и обработка загруженных фото: тип по содержимому, лимит размера, без метаданных."""

import warnings
from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO

from PIL import Image, ImageOps, UnidentifiedImageError

from app.errors import AppError
from app.models.event import MAX_PHOTO_BYTES, THUMB_WIDTH

# Защита от «бомб»: картинка, которая маленькая в файле, но огромная в памяти
MAX_PIXELS = 40_000_000

# Формат Pillow -> MIME и параметры пересохранения
_FORMATS: dict[str, tuple[str, dict[str, object]]] = {
    "JPEG": ("image/jpeg", {"quality": 90, "optimize": True}),
    "PNG": ("image/png", {"optimize": True}),
    "WEBP": ("image/webp", {"quality": 90}),
}


@dataclass(frozen=True)
class ProcessedPhoto:
    data: bytes
    content_type: str
    # Уменьшенная копия: WebP не шире THUMB_WIDTH
    thumb: bytes


def make_thumb(image: Image.Image) -> bytes:
    """WebP не шире THUMB_WIDTH, пропорции сохраняются, маленькие картинки не увеличиваются."""
    copy = image.convert("RGBA" if image.mode in ("RGBA", "LA", "P") else "RGB")
    # Высота не ограничивает: уменьшаем только по ширине
    copy.thumbnail((THUMB_WIDTH, 10_000))
    output = BytesIO()
    copy.save(output, format="WEBP", quality=80)
    return output.getvalue()


def photo_too_large(index: int) -> AppError:
    return AppError(422, "photo_too_large", "Файл больше 2 МБ", extra={"file": index})


def photo_invalid(index: int) -> AppError:
    return AppError(422, "photo_invalid", "Поддерживаются JPEG, PNG и WebP", extra={"file": index})


def read_limited(stream: BinaryIO, index: int) -> bytes:
    """Читает файл целиком, но не больше лимита: лишний байт — сразу отказ."""
    raw = stream.read(MAX_PHOTO_BYTES + 1)
    if len(raw) > MAX_PHOTO_BYTES:
        raise photo_too_large(index)
    return raw


def process_photo(raw: bytes, index: int) -> ProcessedPhoto:
    """Проверяет картинку по содержимому, поворачивает по EXIF и пересохраняет без метаданных."""
    if len(raw) > MAX_PHOTO_BYTES:
        raise photo_too_large(index)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as source:
                if source.format not in _FORMATS:
                    raise photo_invalid(index)
                if source.width * source.height > MAX_PIXELS:
                    raise photo_invalid(index)
                content_type, save_options = _FORMATS[source.format]
                image_format = source.format
                source.load()
                image = ImageOps.exif_transpose(source)
    except AppError:
        raise
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        SyntaxError,
        ValueError,
    ) as exc:
        raise photo_invalid(index) from exc

    # Без EXIF, XMP и прочих метаданных: в них бывают координаты съёмки
    image.info = {}
    if image_format == "JPEG" and image.mode not in ("RGB", "L", "CMYK"):
        image = image.convert("RGB")
    output = BytesIO()
    image.save(output, format=image_format, exif=b"", **save_options)
    return ProcessedPhoto(
        data=output.getvalue(), content_type=content_type, thumb=make_thumb(image)
    )
