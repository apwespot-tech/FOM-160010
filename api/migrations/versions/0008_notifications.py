"""in-app notifications

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

notification_type = postgresql.ENUM(
    "event_changed",
    "event_deleted",
    "participant_removed",
    "participant_joined",
    "participant_left",
    "review_reminder",
    name="notification_type",
    create_type=False,
)


def upgrade() -> None:
    notification_type.create(op.get_bind(), checkfirst=False)
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("type", notification_type, nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("event_title", sa.String(100), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=True),
        sa.Column("changed_fields", postgresql.ARRAY(sa.String(32)), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(type IN ('participant_removed', 'participant_joined', 'participant_left')) "
            "= (participant_id IS NOT NULL)",
            name="ck_notifications_participant_by_type",
        ),
        sa.CheckConstraint(
            "(type = 'event_changed') = (changed_fields IS NOT NULL)",
            name="ck_notifications_changed_fields_by_type",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_notifications_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            name="fk_notifications_event_id_events",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["participant_id"],
            ["users.id"],
            name="fk_notifications_participant_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
    )
    op.create_index(
        "ix_notifications_user_created",
        "notifications",
        ["user_id", sa.text("created_at DESC"), sa.text("id DESC")],
    )
    op.create_index(
        "ix_notifications_user_unread",
        "notifications",
        ["user_id"],
        postgresql_where=sa.text("read_at IS NULL"),
    )
    op.create_index(
        "uq_notifications_review_reminder",
        "notifications",
        ["user_id", "event_id"],
        unique=True,
        postgresql_where=sa.text("type = 'review_reminder'"),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    notification_type.drop(op.get_bind(), checkfirst=False)
