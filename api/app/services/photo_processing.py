"""Проверка и обработка загруженных фото: тип по содержимому, лимит размера, без метаданных."""

import warnings
from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO

from PIL import Image, ImageOps, UnidentifiedImageError

from app.errors import AppError
from app.models.event import MAX_PHOTO_BYTES

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
    return ProcessedPhoto(data=output.getvalue(), content_type=content_type)
