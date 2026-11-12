"""Картинки для тестов, сгенерированные в памяти."""

import zlib
from io import BytesIO

from PIL import Image

ORIENTATION_TAG = 0x0112
GPS_IFD_TAG = 0x8825


def make_image(
    image_format: str = "JPEG",
    size: tuple[int, int] = (40, 30),
    *,
    orientation: int | None = None,
    gps: bool = False,
    color: tuple[int, int, int] = (200, 80, 40),
) -> bytes:
    image = Image.new("RGB", size, color)
    exif = Image.Exif()
    if orientation is not None:
        exif[ORIENTATION_TAG] = orientation
    if gps:
        gps_ifd = exif.get_ifd(GPS_IFD_TAG)
        gps_ifd[1] = "N"
        gps_ifd[2] = (55.0, 45.0, 0.0)
    output = BytesIO()
    options: dict[str, object] = {}
    if orientation is not None or gps:
        options["exif"] = exif.tobytes()
    image.save(output, format=image_format, **options)
    return output.getvalue()


def png_of_size(total: int) -> bytes:
    """Корректный PNG ровно заданного размера: добивается служебным чанком перед IEND."""
    base = make_image("PNG", (4, 4))
    iend = base.rindex(b"IEND") - 4
    padding = total - len(base) - 12
    assert padding >= 0
    chunk_type = b"prVt"
    body = b"\0" * padding
    crc = zlib.crc32(chunk_type + body).to_bytes(4, "big")
    chunk = padding.to_bytes(4, "big") + chunk_type + body + crc
    return base[:iend] + chunk + base[iend:]


def jpeg_of_size(total: int) -> bytes:
    """Корректный JPEG ровно заданного размера: добивается комментариями (COM) после SOI."""
    base = make_image("JPEG", (4, 4))
    missing = total - len(base)
    segments = []
    while missing > 0:
        # Сегмент: маркер (2) + длина (2) + данные; длина включает себя, не больше 65535
        data_len = min(missing - 4, 65533)
        if 0 < missing - (data_len + 4) < 4:
            # Остаток меньше заголовка сегмента — делаем этот сегмент короче
            data_len -= 4
        if data_len < 0:
            raise AssertionError("слишком маленькая добивка")
        segments.append(b"\xff\xfe" + (data_len + 2).to_bytes(2, "big") + b"\0" * data_len)
        missing -= data_len + 4
    return base[:2] + b"".join(segments) + base[2:]
