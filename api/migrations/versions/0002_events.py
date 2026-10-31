"""events, categories and participants

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INITIAL_CATEGORIES = ["Настольные игры", "Прогулки", "Спорт", "Кино"]


def upgrade() -> None:
    categories = op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_categories"),
        sa.UniqueConstraint("name", name="uq_categories_name"),
    )
    op.bulk_insert(categories, [{"name": name} for name in INITIAL_CATEGORIES])

    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organizer_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("description", sa.String(2000), nullable=False),
        sa.Column("place", sa.String(200), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("max_participants", sa.SmallInteger(), nullable=False),
        sa.Column("min_age", sa.SmallInteger(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "max_participants BETWEEN 2 AND 100", name="ck_events_max_participants_range"
        ),
        sa.CheckConstraint("min_age IN (0, 14, 16, 18)", name="ck_events_min_age_values"),
        sa.CheckConstraint("duration_minutes BETWEEN 1 AND 1440", name="ck_events_duration_range"),
        sa.ForeignKeyConstraint(
            ["organizer_id"], ["users.id"], name="fk_events_organizer_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_events_category_id_categories",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_events"),
    )
    op.create_index("ix_events_starts_at", "events", ["starts_at", "id"])
    op.create_index("ix_events_category_id_starts_at", "events", ["category_id", "starts_at"])

    op.create_table(
        "event_participants",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            name="fk_event_participants_event_id_events",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_event_participants_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("event_id", "user_id", name="pk_event_participants"),
    )
    op.create_index("ix_event_participants_user_id", "event_participants", ["user_id"])


def downgrade() -> None:
    op.drop_table("event_participants")
    op.drop_table("events")
    op.drop_table("categories")
