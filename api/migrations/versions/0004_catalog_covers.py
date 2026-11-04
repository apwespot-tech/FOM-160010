"""category icons and covers, photo thumbnails

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-04

Код приложения не импортируется: уменьшение картинок — своё, чтобы будущие изменения
сервиса не меняли историю миграций.
"""

from collections.abc import Sequence
from io import BytesIO
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from PIL import Image

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ASSETS = Path(__file__).resolve().parents[1] / "assets" / "category_covers"
THUMB_WIDTH = 800

# Категория -> (файл картинки, иконка primeicons); совпадает с scripts/generate_category_covers.py
CATEGORY_COVERS = {
    "Настольные игры": ("board-games.webp", "pi-th-large"),
    "Прогулки": ("walks.webp", "pi-map"),
    "Спорт": ("sport.webp", "pi-bolt"),
    "Кино": ("cinema.webp", "pi-video"),
}


def make_thumb(data: bytes) -> bytes:
    """WebP не шире THUMB_WIDTH, пропорции сохраняются, маленькие картинки не увеличиваются."""
    with Image.open(BytesIO(data)) as source:
        image = source.convert("RGBA" if source.mode in ("RGBA", "LA", "P") else "RGB")
    image.thumbnail((THUMB_WIDTH, 10_000))
    output = BytesIO()
    image.save(output, format="WEBP", quality=80)
    return output.getvalue()


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "category_covers",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("content_type", sa.String(20), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("thumb", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "content_type IN ('image/jpeg', 'image/png', 'image/webp')",
            name="ck_category_covers_content_type_values",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_category_covers"),
    )
    op.add_column("categories", sa.Column("icon", sa.String(40), nullable=True))
    op.add_column("categories", sa.Column("cover_id", sa.Uuid(), nullable=True))

    for name, (filename, icon) in CATEGORY_COVERS.items():
        data = (ASSETS / filename).read_bytes()
        cover_id = bind.execute(
            sa.text(
                "INSERT INTO category_covers (content_type, data, thumb) "
                "VALUES ('image/webp', :data, :thumb) RETURNING id"
            ),
            {"data": data, "thumb": make_thumb(data)},
        ).scalar_one()
        bind.execute(
            sa.text("UPDATE categories SET icon = :icon, cover_id = :cover WHERE name = :name"),
            {"icon": icon, "cover": cover_id, "name": name},
        )

    # Категория без картинки или иконки здесь уронит миграцию — так и задумано
    op.alter_column("categories", "icon", nullable=False)
    op.alter_column("categories", "cover_id", nullable=False)
    op.create_check_constraint(
        "ck_categories_icon_format", "categories", "icon ~ '^pi-[a-z0-9-]+$'"
    )
    op.create_foreign_key(
        "fk_categories_cover_id_category_covers",
        "categories",
        "category_covers",
        ["cover_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # Уменьшенные копии для уже сохранённых фото — по одному, без загрузки всех байтов сразу
    op.add_column("event_photo_data", sa.Column("thumb", sa.LargeBinary(), nullable=True))
    photo_ids = bind.execute(sa.text("SELECT photo_id FROM event_photo_data")).scalars().all()
    for photo_id in photo_ids:
        data = bind.execute(
            sa.text("SELECT data FROM event_photo_data WHERE photo_id = :id"), {"id": photo_id}
        ).scalar_one()
        bind.execute(
            sa.text("UPDATE event_photo_data SET thumb = :thumb WHERE photo_id = :id"),
            {"thumb": make_thumb(data), "id": photo_id},
        )
    op.alter_column("event_photo_data", "thumb", nullable=False)


def downgrade() -> None:
    op.drop_column("event_photo_data", "thumb")
    op.drop_constraint("fk_categories_cover_id_category_covers", "categories", type_="foreignkey")
    op.drop_constraint("ck_categories_icon_format", "categories", type_="check")
    op.drop_column("categories", "cover_id")
    op.drop_column("categories", "icon")
    op.drop_table("category_covers")
