"""Проверка и обработка загружаемых фото без HTTP."""

from io import BytesIO

import pytest
from PIL import Image

from app.errors import AppError
from app.models.event import MAX_PHOTO_BYTES
from app.services.photo_processing import process_photo, read_limited
from tests.images import (
    GPS_IFD_TAG,
    ORIENTATION_TAG,
    jpeg_of_size,
    make_image,
    png_of_size,
)


def _error_code(exc: pytest.ExceptionInfo[AppError]) -> str:
    return exc.value.code


def test_exactly_max_size_passes() -> None:
    raw = jpeg_of_size(MAX_PHOTO_BYTES)
    assert len(raw) == MAX_PHOTO_BYTES
    assert read_limited(BytesIO(raw), 0) == raw
    assert process_photo(raw, 0).content_type == "image/jpeg"


def test_png_of_exact_size_is_valid() -> None:
    raw = png_of_size(MAX_PHOTO_BYTES)
    assert len(raw) == MAX_PHOTO_BYTES
    assert process_photo(raw, 0).content_type == "image/png"


def test_one_byte_over_limit_is_rejected() -> None:
    raw = jpeg_of_size(MAX_PHOTO_BYTES + 1)
    with pytest.raises(AppError) as exc:
        read_limited(BytesIO(raw), 2)
    assert _error_code(exc) == "photo_too_large"
    assert exc.value.extra == {"file": 2}
    with pytest.raises(AppError) as exc:
        process_photo(raw, 2)
    assert _error_code(exc) == "photo_too_large"


def test_text_disguised_as_jpeg_is_rejected() -> None:
    with pytest.raises(AppError) as exc:
        process_photo(b"just some text, not a picture", 1)
    assert _error_code(exc) == "photo_invalid"
    assert exc.value.extra == {"file": 1}


def test_gif_is_rejected() -> None:
    with pytest.raises(AppError) as exc:
        process_photo(make_image("GIF"), 0)
    assert _error_code(exc) == "photo_invalid"


def test_truncated_jpeg_is_rejected() -> None:
    raw = make_image("JPEG", (200, 200))
    with pytest.raises(AppError) as exc:
        process_photo(raw[: len(raw) // 2], 0)
    assert _error_code(exc) == "photo_invalid"


@pytest.mark.parametrize(
    ("image_format", "content_type"),
    [("JPEG", "image/jpeg"), ("PNG", "image/png"), ("WEBP", "image/webp")],
)
def test_format_is_preserved(image_format: str, content_type: str) -> None:
    photo = process_photo(make_image(image_format), 0)
    assert photo.content_type == content_type
    with Image.open(BytesIO(photo.data)) as image:
        assert image.format == image_format


def test_gps_exif_is_removed() -> None:
    raw = make_image("JPEG", gps=True)
    with Image.open(BytesIO(raw)) as source:
        assert source.getexif().get_ifd(GPS_IFD_TAG), "исходный файл должен содержать GPS"

    photo = process_photo(raw, 0)

    with Image.open(BytesIO(photo.data)) as image:
        assert image.format == "JPEG"
        assert "exif" not in image.info
        assert len(image.getexif()) == 0
        assert not image.getexif().get_ifd(GPS_IFD_TAG)


def test_orientation_is_applied_and_removed() -> None:
    raw = make_image("JPEG", (400, 300), orientation=6)

    photo = process_photo(raw, 0)

    with Image.open(BytesIO(photo.data)) as image:
        assert image.size == (300, 400)
        assert ORIENTATION_TAG not in image.getexif()


def test_too_many_pixels_is_rejected() -> None:
    # 8000×8000 = 64 Мп: файл маленький, но картинка огромная
    raw = make_image("PNG", (8000, 8000))
    assert len(raw) < MAX_PHOTO_BYTES
    with pytest.raises(AppError) as exc:
        process_photo(raw, 0)
    assert _error_code(exc) == "photo_invalid"


@pytest.mark.parametrize(
    ("image_format", "size", "expected"),
    [
        ("JPEG", (4000, 3000), (800, 600)),
        ("PNG", (1600, 900), (800, 450)),
        ("JPEG", (640, 480), (640, 480)),
    ],
)
def test_thumb_size(image_format: str, size: tuple[int, int], expected: tuple[int, int]) -> None:
    photo = process_photo(make_image(image_format, size), 0)

    with Image.open(BytesIO(photo.thumb)) as thumb:
        assert thumb.format == "WEBP"
        assert thumb.size == expected


def test_thumb_has_no_metadata_and_respects_orientation() -> None:
    photo = process_photo(make_image("JPEG", (1200, 900), orientation=6, gps=True), 0)

    with Image.open(BytesIO(photo.thumb)) as thumb:
        assert thumb.size == (800, 1067)
        assert len(thumb.getexif()) == 0
