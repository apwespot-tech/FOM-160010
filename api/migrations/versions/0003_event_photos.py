"""event photos

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_photos",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("content_type", sa.String(20), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("position BETWEEN 0 AND 9", name="ck_event_photos_position_range"),
        sa.CheckConstraint(
            "content_type IN ('image/jpeg', 'image/png', 'image/webp')",
            name="ck_event_photos_content_type_values",
        ),
        sa.ForeignKeyConstraint(
            ["event_id"], ["events.id"], name="fk_event_photos_event_id_events", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_event_photos"),
        sa.UniqueConstraint(
            "event_id",
            "position",
            name="uq_event_photos_event_id_position",
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    op.create_table(
        "event_photo_data",
        sa.Column("photo_id", sa.Uuid(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(
            ["photo_id"],
            ["event_photos.id"],
            name="fk_event_photo_data_photo_id_event_photos",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("photo_id", name="pk_event_photo_data"),
    )


def downgrade() -> None:
    op.drop_table("event_photo_data")
    op.drop_table("event_photos")
