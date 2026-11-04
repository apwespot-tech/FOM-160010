"""Миграция 0004: иконки и картинки категорий, уменьшенные копии уже сохранённых фото."""

import uuid
from io import BytesIO

from alembic import command
from PIL import Image
from sqlalchemy import create_engine, text

from tests.conftest import alembic_config
from tests.images import make_image


def test_migration_categories_have_icons_and_covers(migrated_db: str) -> None:
    engine = create_engine(migrated_db)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT c.name, c.icon, cc.content_type, cc.data, cc.thumb "
                "FROM categories c JOIN category_covers cc ON cc.id = c.cover_id ORDER BY c.id"
            )
        ).all()
    engine.dispose()

    assert [(name, icon) for name, icon, *_ in rows] == [
        ("Настольные игры", "pi-th-large"),
        ("Прогулки", "pi-map"),
        ("Спорт", "pi-bolt"),
        ("Кино", "pi-video"),
    ]
    for _, _, content_type, data, thumb in rows:
        assert content_type == "image/webp"
        with Image.open(BytesIO(data)) as full:
            assert (full.format, full.size) == ("WEBP", (1200, 675))
        with Image.open(BytesIO(thumb)) as small:
            assert (small.format, small.size) == ("WEBP", (800, 450))


def test_migration_creates_thumbs_for_existing_photos(migrated_db: str) -> None:
    config = alembic_config(migrated_db)
    engine = create_engine(migrated_db)
    user_id, event_id, photo_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    try:
        command.downgrade(config, "0003")
        # Фото, сохранённое до появления уменьшенных копий
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO users (id, phone) VALUES (:id, '+79995550001')"), {"id": user_id}
            )
            conn.execute(
                text(
                    "INSERT INTO events (id, organizer_id, category_id, title, description, place, "
                    "starts_at, max_participants, min_age) VALUES (:id, :user, 1, 't', 'd', 'p', "
                    "now() + interval '1 day', 5, 0)"
                ),
                {"id": event_id, "user": user_id},
            )
            conn.execute(
                text(
                    "INSERT INTO event_photos (id, event_id, position, content_type, size_bytes, "
                    "created_at) VALUES (:id, :event, 0, 'image/jpeg', 1, now())"
                ),
                {"id": photo_id, "event": event_id},
            )
            conn.execute(
                text("INSERT INTO event_photo_data (photo_id, data) VALUES (:id, :data)"),
                {"id": photo_id, "data": make_image("JPEG", (1600, 1200))},
            )

        command.upgrade(config, "head")

        with engine.connect() as conn:
            thumb = conn.execute(
                text("SELECT thumb FROM event_photo_data WHERE photo_id = :id"), {"id": photo_id}
            ).scalar_one()
        with Image.open(BytesIO(thumb)) as image:
            assert (image.format, image.size) == ("WEBP", (800, 600))
    finally:
        command.upgrade(config, "head")
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        engine.dispose()
