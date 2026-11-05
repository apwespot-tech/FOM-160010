"""reviews of organizers and participants

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

review_kind = postgresql.ENUM("organizer", "participant", name="review_kind", create_type=False)


def upgrade() -> None:
    review_kind.create(op.get_bind(), checkfirst=False)
    op.create_table(
        "reviews",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("event_title", sa.String(100), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("kind", review_kind, nullable=False),
        sa.Column("stars", sa.SmallInteger(), nullable=False),
        sa.Column("text", sa.String(1000), nullable=True),
        sa.Column("anonymous", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("stars BETWEEN 1 AND 5", name="ck_reviews_stars_range"),
        sa.CheckConstraint("author_id <> target_id", name="ck_reviews_not_self"),
        sa.ForeignKeyConstraint(
            ["event_id"], ["events.id"], name="fk_reviews_event_id_events", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name="fk_reviews_author_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_id"], ["users.id"], name="fk_reviews_target_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_reviews"),
        sa.UniqueConstraint(
            "event_id", "author_id", "target_id", name="uq_reviews_event_author_target"
        ),
    )
    op.create_index(
        "ix_reviews_target_kind_created",
        "reviews",
        ["target_id", "kind", sa.text("created_at DESC"), sa.text("id DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_reviews_target_kind_created", table_name="reviews")
    op.drop_table("reviews")
    review_kind.drop(op.get_bind(), checkfirst=False)
