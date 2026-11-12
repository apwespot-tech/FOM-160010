"""cities, profile images and interests, event city

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_EVENT_CITY = "Москва"

# Крупные города России: города-миллионники, крупные региональные центры и Сочи
CITIES = [
    "Москва",
    "Санкт-Петербург",
    "Новосибирск",
    "Екатеринбург",
    "Казань",
    "Нижний Новгород",
    "Красноярск",
    "Челябинск",
    "Самара",
    "Уфа",
    "Ростов-на-Дону",
    "Краснодар",
    "Омск",
    "Воронеж",
    "Пермь",
    "Волгоград",
    "Тюмень",
    "Саратов",
    "Тольятти",
    "Ижевск",
    "Барнаул",
    "Иркутск",
    "Хабаровск",
    "Владивосток",
    "Ярославль",
    "Калининград",
    "Томск",
    "Оренбург",
    "Кемерово",
    "Новокузнецк",
    "Рязань",
    "Набережные Челны",
    "Пенза",
    "Липецк",
    "Тула",
    "Киров",
    "Чебоксары",
    "Астрахань",
    "Махачкала",
    "Сочи",
]


def upgrade() -> None:
    cities = op.create_table(
        "cities",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("name", sa.String(60), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_cities"),
        sa.UniqueConstraint("name", name="uq_cities_name"),
    )
    op.bulk_insert(cities, [{"name": name} for name in CITIES])

    op.create_table(
        "user_images",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("content_type", sa.String(20), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("thumb", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "content_type IN ('image/jpeg', 'image/png', 'image/webp')",
            name="ck_user_images_content_type_values",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_images_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_images"),
    )
    op.create_index("ix_user_images_user_id", "user_images", ["user_id"])

    op.create_table(
        "user_interests",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_interests_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_user_interests_category_id_categories",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "category_id", name="pk_user_interests"),
    )

    op.add_column("users", sa.Column("about", sa.String(500), nullable=True))
    op.add_column("users", sa.Column("city_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("avatar_id", sa.Uuid(), nullable=True))
    op.add_column("users", sa.Column("cover_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_users_city_id_cities", "users", "cities", ["city_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_users_avatar_id_user_images",
        "users",
        "user_images",
        ["avatar_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_users_cover_id_user_images",
        "users",
        "user_images",
        ["cover_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # Ссылки на внешние фото не переносим: скачивать картинки с чужих адресов небезопасно
    op.drop_column("users", "photo_url")

    # Город мероприятия обязателен; существующим — Москва
    op.add_column("events", sa.Column("city_id", sa.Integer(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE events SET city_id = (SELECT id FROM cities WHERE name = :name)"
        ).bindparams(name=DEFAULT_EVENT_CITY)
    )
    op.alter_column("events", "city_id", nullable=False)
    op.create_foreign_key(
        "fk_events_city_id_cities", "events", "cities", ["city_id"], ["id"], ondelete="RESTRICT"
    )


def downgrade() -> None:
    op.drop_constraint("fk_events_city_id_cities", "events", type_="foreignkey")
    op.drop_column("events", "city_id")
    op.add_column("users", sa.Column("photo_url", sa.Text(), nullable=True))
    op.drop_constraint("fk_users_cover_id_user_images", "users", type_="foreignkey")
    op.drop_constraint("fk_users_avatar_id_user_images", "users", type_="foreignkey")
    op.drop_constraint("fk_users_city_id_cities", "users", type_="foreignkey")
    op.drop_column("users", "cover_id")
    op.drop_column("users", "avatar_id")
    op.drop_column("users", "city_id")
    op.drop_column("users", "about")
    op.drop_table("user_interests")
    op.drop_index("ix_user_images_user_id", table_name="user_images")
    op.drop_table("user_images")
    op.drop_table("cities")
